"""FastAPI-app: dunne serving-laag, traint nooit zelf. Laadt bij import een
expliciet gepinde modelversie (MODEL_VERSION) — hard-fail als die ontbreekt
of niet bestaat, nooit een impliciet 'laatste' model."""
from __future__ import annotations

import time
from pathlib import Path
from typing import NamedTuple, Optional

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db import api_keys as db_api_keys
from db import gebruikers as db_gebruikers
from db import sessies as db_sessies
from db import winkels as db_winkels
from db.schema import gebruikers as gebruikers_tabel
from db.schema import maak_database
from security import audit
from serving.config import laad_settings
from serving.forecast import (
    HorizonBuitenBereik,
    OnbekendeWinkel,
    dagreeks,
    voorspel_periode,
    winkel_samenvatting,
)
from serving.schemas import (
    ApiKeyAanmakenVerzoek,
    ApiKeyResponse,
    DagVoorspelling,
    FactorBijdrage,
    ForecastResponse,
    ForecastVerzoek,
    GebruikerAanmakenVerzoek,
    GebruikerResponse,
    LoginVerzoek,
    MetricsResponse,
    NieuweApiKeyResponse,
    PortfolioKpi,
    PortfolioResponse,
    WinkelResponse,
    WinkelSamenvatting,
)
from training.artifact import laad_artefact

settings = laad_settings()
artefact = laad_artefact(settings.models_dir, settings.model_version, versleuteld=settings.encrypt_at_rest)
tenants_db = maak_database(settings.tenants_db_pad)


def _rate_limit_key(request: Request) -> str:
    """Rate-limit per organisatie, niet per losse API-key of bron-IP: twee
    keys van dezelfde klant (bv. kassasysteem + eigen integratie) mogen
    niet elk een eigen budget krijgen, anders verdubbelt de effectieve
    limiet naarmate een organisatie meer keys aanmaakt (Fase 4 Stap 6
    maakte zelfbediende keys pas echt waarschijnlijk). Doet dezelfde
    DB-lookup als vereis_api_key(): slowapi roept dit aan vóórdat FastAPI's
    dependency-resolutie draait, dus er is nog geen geverifieerde
    GeauthenticeerdeKey beschikbaar om organisatie_id uit te lezen. Valt
    terug op het IP-adres als er geen (geldige) key is — dan is er ook geen
    organisatie om op te groeperen."""
    sleutel = request.headers.get("X-API-Key")
    if not sleutel:
        return get_remote_address(request)
    resultaat = db_api_keys.vind_organisatie_voor_key(tenants_db, sleutel)
    if resultaat is None:
        return get_remote_address(request)
    _, organisatie_id = resultaat
    return f"org:{organisatie_id}"


limiter = Limiter(key_func=_rate_limit_key)

app = FastAPI(
    title="Tessar Vraagvoorspelling",
    docs_url="/docs" if settings.expose_docs else None,
    redoc_url="/redoc" if settings.expose_docs else None,
    openapi_url="/openapi.json" if settings.expose_docs else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class GeauthenticeerdeKey(NamedTuple):
    naam: str
    organisatie_id: int


SESSIE_COOKIE_NAAM = "sessie"


class GeauthenticeerdeGebruiker(NamedTuple):
    gebruiker_id: int
    organisatie_id: int
    rol: str
    email: str


def vereis_sessie(request: Request) -> GeauthenticeerdeGebruiker:
    token = request.cookies.get(SESSIE_COOKIE_NAAM)
    if not token:
        raise HTTPException(status_code=401, detail="Niet ingelogd.")
    gebruiker_id = db_sessies.vind_gebruiker_voor_sessie(tenants_db, token)
    if gebruiker_id is None:
        raise HTTPException(status_code=401, detail="Sessie ongeldig of verlopen.")
    with tenants_db.connect() as conn:
        rij = conn.execute(select(gebruikers_tabel).where(gebruikers_tabel.c.id == gebruiker_id)).one()
    return GeauthenticeerdeGebruiker(
        gebruiker_id=rij.id, organisatie_id=rij.organisatie_id, rol=rij.rol, email=rij.email
    )


def vereis_eigenaar(gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)) -> GeauthenticeerdeGebruiker:
    if gebruiker.rol != "eigenaar":
        raise HTTPException(status_code=403, detail="Alleen de eigenaar van de organisatie mag dit.")
    return gebruiker


def vereis_toegang(request: Request, sleutel: Optional[str] = Security(api_key_header)) -> GeauthenticeerdeKey:
    """Accepteert zowel een API-key (externe integraties, bv. een
    kassasysteem — Fase 4 Stap 6) als een geldige sessiecookie (het
    ingelogde dashboard) — allebei resolven naar dezelfde
    GeauthenticeerdeKey-vorm, zodat /forecast, /metrics en /winkels geen
    onderscheid hoeven te maken tussen de twee toegangswegen. Probeert de
    API-key eerst als die is meegegeven; valt anders terug op de
    sessiecookie."""
    if sleutel:
        resultaat = db_api_keys.vind_organisatie_voor_key(tenants_db, sleutel)
        if resultaat is None:
            raise HTTPException(status_code=401, detail="Ongeldige API-key.")
        naam, organisatie_id = resultaat
        return GeauthenticeerdeKey(naam=naam, organisatie_id=organisatie_id)

    token = request.cookies.get(SESSIE_COOKIE_NAAM)
    if token:
        gebruiker_id = db_sessies.vind_gebruiker_voor_sessie(tenants_db, token)
        if gebruiker_id is not None:
            with tenants_db.connect() as conn:
                rij = conn.execute(select(gebruikers_tabel).where(gebruikers_tabel.c.id == gebruiker_id)).one()
            return GeauthenticeerdeKey(naam=rij.email, organisatie_id=rij.organisatie_id)

    raise HTTPException(status_code=401, detail="Niet ingelogd en geen geldige API-key.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_versie": settings.model_version}


@app.post("/login")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute", key_func=get_remote_address)
def login(request: Request, response: Response, verzoek: LoginVerzoek) -> dict:
    gebruiker_id = db_gebruikers.verifieer_inloggegevens(tenants_db, email=verzoek.email, wachtwoord=verzoek.wachtwoord)
    if gebruiker_id is None:
        raise HTTPException(status_code=401, detail="Ongeldige inloggegevens.")

    token = db_sessies.maak_sessie(tenants_db, gebruiker_id=gebruiker_id)
    response.set_cookie(
        SESSIE_COOKIE_NAAM,
        token,
        httponly=True,
        secure=settings.sessie_cookie_secure,
        samesite="lax",
        max_age=int(db_sessies.STANDAARD_GELDIGHEIDSDUUR.total_seconds()),
    )
    return {"status": "ok"}


@app.post("/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(SESSIE_COOKIE_NAAM)
    if token:
        db_sessies.verwijder_sessie(tenants_db, token)
    response.delete_cookie(SESSIE_COOKIE_NAAM)
    return {"status": "ok"}


@app.get("/me")
def me(gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)) -> dict:
    return {"email": gebruiker.email, "rol": gebruiker.rol, "organisatie_id": gebruiker.organisatie_id}


@app.post("/gebruikers", response_model=GebruikerResponse, status_code=201)
def gebruiker_aanmaken(
    verzoek: GebruikerAanmakenVerzoek, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)
) -> GebruikerResponse:
    # Een zelf-aangemaakte gebruiker is altijd "lid" — een tweede eigenaar
    # toevoegen kan alleen via db/gebruikers_cli.py (operatorhandeling),
    # om onbedoelde privilege-escalatie via dit endpoint uit te sluiten.
    try:
        gebruiker_id = db_gebruikers.maak_gebruiker(
            tenants_db, organisatie_id=eigenaar.organisatie_id, email=verzoek.email, wachtwoord=verzoek.wachtwoord
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail=f"E-mailadres {verzoek.email} is al in gebruik.")
    return GebruikerResponse(id=gebruiker_id, email=verzoek.email, rol="lid", actief=True)


@app.get("/gebruikers", response_model=list[GebruikerResponse])
def gebruikers_lijst(gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)) -> list[GebruikerResponse]:
    with tenants_db.connect() as conn:
        rijen = conn.execute(
            select(gebruikers_tabel).where(gebruikers_tabel.c.organisatie_id == gebruiker.organisatie_id)
        ).all()
    return [GebruikerResponse(id=r.id, email=r.email, rol=r.rol, actief=r.actief) for r in rijen]


@app.post("/api-keys", response_model=NieuweApiKeyResponse, status_code=201)
def api_key_aanmaken(
    verzoek: ApiKeyAanmakenVerzoek, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)
) -> NieuweApiKeyResponse:
    key_id, ruwe_key = db_api_keys.maak_api_key(tenants_db, organisatie_id=eigenaar.organisatie_id, naam=verzoek.naam)
    return NieuweApiKeyResponse(id=key_id, naam=verzoek.naam, ruwe_key=ruwe_key)


@app.get("/api-keys", response_model=list[ApiKeyResponse])
def api_keys_lijst(eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)) -> list[ApiKeyResponse]:
    rijen = db_api_keys.lijst_api_keys(tenants_db, organisatie_id=eigenaar.organisatie_id)
    return [ApiKeyResponse(id=r.id, naam=r.naam, actief=r.actief, aangemaakt_op=r.aangemaakt_op) for r in rijen]


@app.delete("/api-keys/{key_id}", status_code=204)
def api_key_intrekken(key_id: int, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)) -> None:
    # Zelfde 404-i.p.v.-403-redenering als bij store_id hierboven: een
    # andermans key-id bestaat niet voor jou, punt.
    gelukt = db_api_keys.deactiveer_api_key(tenants_db, organisatie_id=eigenaar.organisatie_id, key_id=key_id)
    if not gelukt:
        raise HTTPException(status_code=404, detail=f"Onbekende API-key: {key_id}")


@app.post("/forecast", response_model=ForecastResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def forecast(
    request: Request, verzoek: ForecastVerzoek, key: GeauthenticeerdeKey = Depends(vereis_toegang)
) -> ForecastResponse:
    # Isolatie- en horizon-check zitten binnen dezelfde try/finally als de
    # voorspelling zelf, zodat een geweigerde cross-tenant-poging net zo
    # goed in de audit-log komt als een geslaagd verzoek — een operator
    # moet probeerpogingen op andermans store_id kunnen zien, niet alleen
    # geslaagde aanroepen.
    start = time.monotonic()
    statuscode = 500
    try:
        if not db_winkels.hoort_store_bij_organisatie(tenants_db, verzoek.store_id, key.organisatie_id):
            statuscode = 404
            # Zelfde foutmelding als OnbekendeWinkel hieronder: een 403 zou
            # bevestigen "dit store_id bestaat, is alleen niet van jou",
            # wat andermans store-ID's enumereerbaar maakt. 404 laat
            # "bestaat niet" en "is niet van jou" ononderscheidbaar.
            raise HTTPException(status_code=404, detail=f"Onbekend store_id: {verzoek.store_id}")

        gevalideerde_horizon = artefact["metadata"]["gevalideerde_horizon_dagen"]
        if verzoek.horizon_dagen > gevalideerde_horizon:
            statuscode = 422
            raise HTTPException(
                status_code=422,
                detail=(
                    f"horizon_dagen ({verzoek.horizon_dagen}) overschrijdt de tijdens training "
                    f"gevalideerde periode ({gevalideerde_horizon} dagen)."
                ),
            )

        resultaat = voorspel_periode(
            modellen=artefact["modellen"],
            historie=artefact["historie"],
            winkel_metadata=artefact["winkel_metadata"],
            store_id=verzoek.store_id,
            start_datum=verzoek.start_datum,
            horizon_dagen=verzoek.horizon_dagen,
            promo_datums=dagreeks(verzoek.promo_van, verzoek.promo_tot),
            schoolvakantie_datums=dagreeks(verzoek.schoolvakantie_van, verzoek.schoolvakantie_tot),
            verklaar=True,
        )
        statuscode = 200
    except OnbekendeWinkel:
        statuscode = 404
        raise HTTPException(status_code=404, detail=f"Onbekend store_id: {verzoek.store_id}")
    except HorizonBuitenBereik as e:
        statuscode = 422
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        audit.log(
            settings.audit_log_file,
            {
                "key": key.naam,
                "organisatie_id": key.organisatie_id,
                "store_id": verzoek.store_id,
                "horizon_dagen": verzoek.horizon_dagen,
                "statuscode": statuscode,
                "latency_ms": round((time.monotonic() - start) * 1000, 1),
            },
            versleuteld=settings.encrypt_at_rest,
        )

    return ForecastResponse(
        store_id=verzoek.store_id,
        voorspellingen=[
            DagVoorspelling(datum=rij["Date"].date(), p10=rij["p10"], p50=rij["p50"], p90=rij["p90"])
            for _, rij in resultaat.voorspellingen.iterrows()
        ],
        belangrijkste_factoren=[FactorBijdrage(**f) for f in resultaat.belangrijkste_factoren],
    )


@app.get("/metrics", response_model=MetricsResponse)
def metrics(key: GeauthenticeerdeKey = Depends(vereis_toegang)) -> MetricsResponse:
    m = artefact["metadata"]
    return MetricsResponse(
        model_versie=m["versie"],
        rmspe=m["metrics"]["rmspe"],
        coverage_p10_p90=m["metrics"]["coverage_p10_p90"],
        n_observaties=m["metrics"]["n_observaties"],
        gevalideerde_horizon_dagen=m["gevalideerde_horizon_dagen"],
        trainingsperiode_eind=m["trainingsperiode_eind"][:10],
    )


@app.get("/winkels", response_model=list[WinkelResponse])
def winkels_lijst(key: GeauthenticeerdeKey = Depends(vereis_toegang)) -> list[WinkelResponse]:
    rijen = db_winkels.lijst_winkels(tenants_db, organisatie_id=key.organisatie_id)
    return [WinkelResponse(extern_store_id=r.extern_store_id, naam=r.naam) for r in rijen]


@app.get("/portfolio", response_model=PortfolioResponse)
def portfolio(
    horizon_dagen: int = Query(7, gt=0),
    limiet: int = Query(50, gt=0, le=200),
    offset: int = Query(0, ge=0),
    key: GeauthenticeerdeKey = Depends(vereis_toegang),
) -> PortfolioResponse:
    # Berekent bewust alleen de opgevraagde pagina, nooit alle winkels van
    # een organisatie in één keer: een volledige live-berekening voor de
    # 1115 winkels van de lokale demo-organisatie kost ~88 seconden
    # (gemeten) — te traag voor één synchrone aanvraag. Een echte klant
    # heeft naar verwachting een paar winkels (zie FASE4-SAAS-FOUNDATION.md,
    # beslissing 5), dus past sowieso al binnen één pagina.
    gevalideerde_horizon = artefact["metadata"]["gevalideerde_horizon_dagen"]
    if horizon_dagen > gevalideerde_horizon:
        raise HTTPException(
            status_code=422,
            detail=(
                f"horizon_dagen ({horizon_dagen}) overschrijdt de tijdens training "
                f"gevalideerde periode ({gevalideerde_horizon} dagen)."
            ),
        )

    alle_winkels = db_winkels.lijst_winkels(tenants_db, organisatie_id=key.organisatie_id)
    pagina = alle_winkels[offset:offset + limiet]

    start_datum = pd.Timestamp(artefact["metadata"]["trainingsperiode_eind"][:10]) + pd.Timedelta(days=1)
    winkel_samenvattingen = []
    for rij in pagina:
        try:
            samenvatting = winkel_samenvatting(
                modellen=artefact["modellen"], historie=artefact["historie"],
                winkel_metadata=artefact["winkel_metadata"],
                store_id=rij.extern_store_id, start_datum=start_datum, horizon_dagen=horizon_dagen,
            )
        except (OnbekendeWinkel, HorizonBuitenBereik):
            # Winkel bestaat in tenants.db maar niet (meer) in het huidige
            # modelartefact, of heeft onvoldoende historie voor deze
            # horizon — overslaan i.p.v. de hele pagina te laten falen.
            continue
        winkel_samenvattingen.append(
            WinkelSamenvatting(extern_store_id=rij.extern_store_id, naam=rij.naam, **samenvatting)
        )

    kpi = PortfolioKpi(
        totale_verwachte_omzet=sum(w.totaal_p50 for w in winkel_samenvattingen),
        model_nauwkeurigheid_rmspe=artefact["metadata"]["metrics"]["rmspe"],
        aantal_afwijkend=sum(1 for w in winkel_samenvattingen if w.afwijkend),
    )
    return PortfolioResponse(
        winkels=winkel_samenvattingen, totaal_winkels=len(alle_winkels), offset=offset, limiet=limiet, kpi=kpi,
    )


_dashboard_pad = Path(__file__).resolve().parent.parent / "dashboard"
if _dashboard_pad.exists():
    app.mount("/", StaticFiles(directory=str(_dashboard_pad), html=True), name="dashboard")
