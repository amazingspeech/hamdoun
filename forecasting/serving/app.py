"""FastAPI-app: dunne serving-laag, traint nooit zelf. Laadt bij import een
expliciet gepinde modelversie (MODEL_VERSION) — hard-fail als die ontbreekt
of niet bestaat, nooit een impliciet 'laatste' model."""
from __future__ import annotations

import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple, Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, Security, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db import aanmeldingen as db_aanmeldingen
from db import api_keys as db_api_keys
from db import gebruiker_winkels as db_gebruiker_winkels
from db import gebruikers as db_gebruikers
from db import organisaties as db_organisaties
from db import product_verkoopdata as db_product_verkoopdata
from db import sessies as db_sessies
from db import verkoopdata as db_verkoopdata
from db import wachtwoord_reset as db_wachtwoord_reset
from db import winkels as db_winkels
from db.bootstrap import bootstrap_organisatie
from db.schema import gebruikers as gebruikers_tabel
from db.schema import maak_database
from security import audit, mail
from security.api_keys import hash_key
from serving.betaalintegratie import OngeldigeWebhookSignature, lees_webhook_event, maak_checkout_sessie
from serving.config import laad_settings
from serving.eigen_voorspelling import MINIMUM_DAGEN, bereken_eigen_voorspelling
from serving.herbestel_advies_per_product import bereken_herbestel_advies_per_product
from serving.forecast import (
    HorizonBuitenBereik,
    OnbekendeWinkel,
    dagreeks,
    herbestel_advies,
    voorspel_periode,
    vorige_periode_omzet,
    winkel_samenvatting,
)
from serving.schemas import (
    ApiKeyAanmakenVerzoek,
    ApiKeyResponse,
    DagVoorspelling,
    EigenVoorspellingDag,
    EigenVoorspellingResponse,
    FactorBijdrage,
    ForecastResponse,
    ForecastVerzoek,
    GebruikerAanmakenVerzoek,
    GebruikerResponse,
    HerbestelAdvies,
    LoginVerzoek,
    MetricsResponse,
    ModelVersieMetric,
    NieuweApiKeyResponse,
    OrganisatieInstellingenResponse,
    OrganisatieInstellingenVerzoek,
    PortfolioKpi,
    PortfolioResponse,
    ProductHerbestelAdviesResponse,
    ProductVerkoopdataUploadResponse,
    SignupResponse,
    SignupVerzoek,
    VerkoopdataResponse,
    VerkoopdataRij,
    VerkoopdataUploadResponse,
    WachtwoordResetAanvraagVerzoek,
    WachtwoordResetVoltooienVerzoek,
    WinkelResponse,
    WinkelSamenvatting,
    WinkelToewijzingResponse,
    WinkelToewijzingVerzoek,
)
from serving.product_verkoopdata import OngeldigeProductVerkoopdata, parse_product_verkoopdata_csv
from serving.verkoopdata import OngeldigeVerkoopdata, parse_verkoopdata_csv
from training.artifact import laad_artefact, lijst_metadata_per_versie

# Alleen voor lokale ontwikkeling: laadt forecasting/.env als het bestaat
# (nooit in Docker gebruikt, zie deploy/DEPLOY.md — daar zet docker compose
# de omgeving direct). Overschrijft nooit een al-gezette omgevingsvariabele
# (python-dotenv's default), dus dit is een no-op zolang de omgeving zelf
# al alles levert, zoals in CI en de testsuite.
load_dotenv()

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
    # gebruiker_id/rol: alleen gevuld via de sessiecookie-weg (het
    # ingelogde dashboard) — een API-key is niet aan een specifieke
    # gebruiker gekoppeld (zie db/api_keys.py), dus blijft altijd org-breed
    # werken. Winkeltoewijzing (portfolio-dashboard item 10) geldt daarom
    # alleen als rol == "lid"; None betekent "geen restrictie toepassen".
    gebruiker_id: Optional[int] = None
    rol: Optional[str] = None


SESSIE_COOKIE_NAAM = "sessie"
# Fase 5 premium-fundament: 14 dagen proberen, dan automatisch een eerste
# incasso — vastgelegde productbeslissing, geen omgevingsvariabele omdat
# dit geen deployment-instelling is. Dezelfde waarde stuurt zowel Stripe's
# eigen trial_period_days (POST /signup) als de lokale trial_verloopt_op
# die db.organisaties.is_in_proefperiode gebruikt (POST /webhooks/stripe)
# — beide moeten in sync blijven.
SIGNUP_PROEFPERIODE_DAGEN = 14


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
    # Een bestaande sessie overleeft een deactivatie (bv. Stripe
    # customer.subscription.deleted, zie POST /webhooks/stripe) niet — dit
    # loopt op elk geauthenticeerd verzoek, niet alleen bij het inloggen.
    if not db_organisaties.is_actief(tenants_db, rij.organisatie_id):
        raise HTTPException(status_code=403, detail="Deze organisatie is niet meer actief.")
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
        if not db_organisaties.is_actief(tenants_db, organisatie_id):
            raise HTTPException(status_code=403, detail="Deze organisatie is niet meer actief.")
        return GeauthenticeerdeKey(naam=naam, organisatie_id=organisatie_id)

    token = request.cookies.get(SESSIE_COOKIE_NAAM)
    if token:
        gebruiker_id = db_sessies.vind_gebruiker_voor_sessie(tenants_db, token)
        if gebruiker_id is not None:
            with tenants_db.connect() as conn:
                rij = conn.execute(select(gebruikers_tabel).where(gebruikers_tabel.c.id == gebruiker_id)).one()
            if not db_organisaties.is_actief(tenants_db, rij.organisatie_id):
                raise HTTPException(status_code=403, detail="Deze organisatie is niet meer actief.")
            return GeauthenticeerdeKey(
                naam=rij.email, organisatie_id=rij.organisatie_id, gebruiker_id=rij.id, rol=rij.rol
            )

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

    with tenants_db.connect() as conn:
        organisatie_id = conn.execute(
            select(gebruikers_tabel.c.organisatie_id).where(gebruikers_tabel.c.id == gebruiker_id)
        ).scalar_one()
    if not db_organisaties.is_actief(tenants_db, organisatie_id):
        raise HTTPException(status_code=403, detail="Deze organisatie is niet meer actief.")

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


@app.post("/wachtwoord-reset/aanvragen")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute", key_func=get_remote_address)
def wachtwoord_reset_aanvragen(request: Request, verzoek: WachtwoordResetAanvraagVerzoek) -> dict:
    """Altijd dezelfde generieke response, ongeacht of het e-mailadres
    bestaat of het versturen lukt — lekt nooit welke e-mailadressen een
    account hebben (zelfde principe als /login en /signup's
    email_is_in_gebruik-check). Rate-limited per IP, want dit endpoint
    stuurt e-mail naar een door de aanvrager opgegeven adres."""
    try:
        gebruiker_id = db_gebruikers.vind_gebruiker_id_via_email(tenants_db, email=verzoek.email)
        if gebruiker_id is not None and settings.app_basis_url:
            token = db_wachtwoord_reset.maak_reset_token(tenants_db, gebruiker_id=gebruiker_id)
            link = f"{settings.app_basis_url}/wachtwoord-resetten.html?token={token}"
            mail.verstuur(
                smtp_host=settings.mail_smtp_host, smtp_poort=settings.mail_smtp_poort,
                afzender=settings.mail_afzender, smtp_gebruiker=settings.mail_smtp_gebruiker,
                smtp_wachtwoord=settings.mail_smtp_wachtwoord,
                ontvanger=verzoek.email, onderwerp="Wachtwoord resetten",
                tekst=(
                    "Je hebt een wachtwoord-reset aangevraagd voor Vraagvoorspelling.\n\n"
                    f"Klik op deze link om een nieuw wachtwoord in te stellen: {link}\n\n"
                    "Deze link is 1 uur geldig. Heb je dit niet aangevraagd, negeer dan deze e-mail."
                ),
            )
    except Exception as e:
        print(f"Wachtwoord-reset-mail voor {verzoek.email!r} mislukt: {e}", file=sys.stderr)
    return {"status": "ok"}


@app.post("/wachtwoord-reset/voltooien")
def wachtwoord_reset_voltooien(verzoek: WachtwoordResetVoltooienVerzoek) -> dict:
    gebruiker_id = db_wachtwoord_reset.vind_gebruiker_voor_reset_token(tenants_db, verzoek.token)
    if gebruiker_id is None:
        raise HTTPException(status_code=400, detail="Ongeldige of verlopen reset-link.")

    db_gebruikers.wijzig_wachtwoord(tenants_db, gebruiker_id=gebruiker_id, nieuw_wachtwoord=verzoek.nieuw_wachtwoord)
    db_wachtwoord_reset.markeer_reset_token_gebruikt(tenants_db, verzoek.token)
    # Elke bestaande sessie ongeldig maken, niet alleen het wachtwoord
    # wijzigen — zie db.sessies.verwijder_sessies_voor_gebruiker.
    db_sessies.verwijder_sessies_voor_gebruiker(tenants_db, gebruiker_id=gebruiker_id)
    return {"status": "ok"}


@app.get("/me")
def me(gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)) -> dict:
    trial_verloopt_op = db_organisaties.haal_trial_verloopt_op(tenants_db, gebruiker.organisatie_id)
    return {
        "email": gebruiker.email, "rol": gebruiker.rol, "organisatie_id": gebruiker.organisatie_id,
        "in_proefperiode": db_organisaties.is_in_proefperiode(tenants_db, gebruiker.organisatie_id),
        "trial_verloopt_op": trial_verloopt_op.date().isoformat() if trial_verloopt_op else None,
    }


@app.post("/signup", response_model=SignupResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute", key_func=get_remote_address)
def signup(request: Request, verzoek: SignupVerzoek) -> SignupResponse:
    """Publiek, geen sessie nodig — start een Stripe Checkout Session met
    proefperiode. De organisatie + eigenaar-account bestaan hierna nog
    NIET; die ontstaan pas als Stripe de betaling bevestigt via
    POST /webhooks/stripe. Zie db/aanmeldingen.py voor de tussentoestand."""
    if not all([
        settings.stripe_secret_key, settings.stripe_price_id, settings.stripe_price_id_extra_lid,
        settings.stripe_price_id_extra_winkel, settings.app_basis_url,
    ]):
        raise HTTPException(status_code=503, detail="Self-serve aanmelden is nog niet geconfigureerd.")

    if db_gebruikers.email_is_in_gebruik(tenants_db, email=verzoek.email):
        raise HTTPException(status_code=409, detail=f"E-mailadres {verzoek.email} is al in gebruik.")

    wachtwoord_hash, wachtwoord_salt = hash_key(verzoek.wachtwoord)
    slug = db_aanmeldingen.genereer_unieke_organisatie_slug(tenants_db, verzoek.organisatie_naam)

    # Herhaalde KVK-aanmelding wordt bewust NIET geblokkeerd (de eigenaar
    # wil juist meerdere bedrijven onder één KVK aanmoedigen), maar krijgt
    # geen gratis proefperiode meer — zie spec.
    was_kvk_herhaling = db_organisaties.kvk_nummer_heeft_organisatie(tenants_db, verzoek.kvk_nummer)

    extra_line_items = []
    if verzoek.aantal_leden > 1:
        extra_line_items.append(
            {"price": settings.stripe_price_id_extra_lid, "quantity": verzoek.aantal_leden - 1}
        )
    if verzoek.aantal_winkels > 1:
        extra_line_items.append(
            {"price": settings.stripe_price_id_extra_winkel, "quantity": verzoek.aantal_winkels - 1}
        )

    sessie = maak_checkout_sessie(
        stripe_secret_key=settings.stripe_secret_key,
        price_id=settings.stripe_price_id,
        klant_email=verzoek.email,
        success_url=f"{settings.app_basis_url}/signup-gelukt.html",
        cancel_url=f"{settings.app_basis_url}/signup.html",
        metadata={"organisatie_naam": verzoek.organisatie_naam},
        proefperiode_dagen=None if was_kvk_herhaling else SIGNUP_PROEFPERIODE_DAGEN,
        extra_line_items=extra_line_items or None,
    )

    db_aanmeldingen.maak_aanmelding(
        tenants_db,
        organisatie_naam=verzoek.organisatie_naam,
        organisatie_slug=slug,
        email=verzoek.email,
        wachtwoord_hash=wachtwoord_hash,
        wachtwoord_salt=wachtwoord_salt,
        stripe_checkout_session_id=sessie.id,
        kvk_nummer=verzoek.kvk_nummer,
        aantal_leden=verzoek.aantal_leden,
        aantal_winkels=verzoek.aantal_winkels,
        was_kvk_herhaling=was_kvk_herhaling,
    )
    return SignupResponse(checkout_url=sessie.checkout_url)


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict:
    """Rondt een self-serve aanmelding af zodra Stripe checkout.session.
    completed meldt (betaalmethode vastgelegd, proefperiode gestart). Geen
    sessie/API-key-auth — dit endpoint authenticeert via de Stripe-
    signature op de payload zelf (zie serving.betaalintegratie). Idempotent:
    Stripe kan hetzelfde event meermaals afleveren, en aanmelding.
    organisatie_id (al gezet = al verwerkt) voorkomt een tweede organisatie/
    gebruiker."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe-webhook is nog niet geconfigureerd.")

    payload = await request.body()
    signature_header = request.headers.get("stripe-signature", "")
    try:
        event = lees_webhook_event(
            payload=payload, signature_header=signature_header, webhook_secret=settings.stripe_webhook_secret
        )
    except OngeldigeWebhookSignature:
        raise HTTPException(status_code=400, detail="Ongeldige Stripe-signature.")

    if event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        organisatie_id = db_organisaties.haal_organisatie_id_bij_stripe_subscription(tenants_db, subscription["id"])
        if organisatie_id is None:
            return {"status": "genegeerd"}
        db_organisaties.deactiveer_organisatie(tenants_db, organisatie_id)
        return {"status": "ok"}

    if event["type"] != "checkout.session.completed":
        return {"status": "genegeerd"}

    sessie = event["data"]["object"]
    aanmelding = db_aanmeldingen.haal_aanmelding_bij_sessie(tenants_db, sessie["id"])
    if aanmelding is None:
        return {"status": "genegeerd"}
    if aanmelding.organisatie_id is not None:
        return {"status": "al_verwerkt"}

    # Eén gedeelde transactie voor alle vier schrijfacties: als Stripe deze
    # aflevering herhaalt na een fout halverwege (bv. een tijdelijke
    # DB-storing na het aanmaken van de organisatie), mag er nooit een
    # gedeeltelijk resultaat blijven staan — dat zou de retry laten
    # stuklopen op de unique constraint van organisaties.slug/gebruikers.
    # email. Ofwel alles lukt, ofwel niets (rollback), nooit iets ertussenin.
    with tenants_db.begin() as conn:
        org_id = bootstrap_organisatie(
            tenants_db, naam=aanmelding.organisatie_naam, slug=aanmelding.organisatie_slug, store_ids=[], conn=conn,
            trial_verloopt_op=datetime.now(timezone.utc) + timedelta(days=SIGNUP_PROEFPERIODE_DAGEN),
        )
        db_gebruikers.maak_gebruiker_met_hash(
            tenants_db, organisatie_id=org_id, email=aanmelding.email,
            wachtwoord_hash=aanmelding.wachtwoord_hash, wachtwoord_salt=aanmelding.wachtwoord_salt,
            rol="eigenaar", conn=conn,
        )
        db_organisaties.stel_stripe_koppeling_in(
            tenants_db, organisatie_id=org_id,
            # Itemtoegang, geen .get(): een echt Stripe-object (StripeObject)
            # ondersteunt geen .get() zoals een plain dict — zie
            # _NepStripeObject in tests/test_stripe_webhook_endpoint.py.
            # customer/subscription staan altijd gevuld op dit punt in een
            # subscription-mode Checkout.
            stripe_customer_id=sessie["customer"], stripe_subscription_id=sessie["subscription"], conn=conn,
        )
        db_aanmeldingen.voltooi_aanmelding(tenants_db, aanmelding_id=aanmelding.id, organisatie_id=org_id, conn=conn)

    return {"status": "ok"}


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


@app.get("/gebruikers/{gebruiker_id}/winkels", response_model=WinkelToewijzingResponse)
def winkeltoewijzing_lezen(
    gebruiker_id: int, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)
) -> WinkelToewijzingResponse:
    doelgebruiker = db_gebruikers.haal_gebruiker(
        tenants_db, gebruiker_id=gebruiker_id, organisatie_id=eigenaar.organisatie_id
    )
    if doelgebruiker is None:
        raise HTTPException(status_code=404, detail=f"Onbekende gebruiker: {gebruiker_id}")
    winkel_ids = db_gebruiker_winkels.lijst_toegewezen_winkels(tenants_db, gebruiker_id=gebruiker_id)
    return WinkelToewijzingResponse(winkel_ids=winkel_ids)


@app.put("/gebruikers/{gebruiker_id}/winkels", response_model=WinkelToewijzingResponse)
def winkeltoewijzing_instellen(
    gebruiker_id: int,
    verzoek: WinkelToewijzingVerzoek,
    eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar),
) -> WinkelToewijzingResponse:
    # Auditlogging hier om dezelfde reden als bij /forecast: dit endpoint
    # verandert wie welke data mag zien, dus een operator moet kunnen zien
    # wie wanneer welke toewijzing heeft ingesteld — niet alleen geslaagde
    # aanroepen (via finally), net als de tenant-isolatie-check elders.
    start = time.monotonic()
    statuscode = 500
    try:
        doelgebruiker = db_gebruikers.haal_gebruiker(
            tenants_db, gebruiker_id=gebruiker_id, organisatie_id=eigenaar.organisatie_id
        )
        if doelgebruiker is None:
            statuscode = 404
            raise HTTPException(status_code=404, detail=f"Onbekende gebruiker: {gebruiker_id}")
        if doelgebruiker.rol != "lid":
            statuscode = 422
            raise HTTPException(
                status_code=422, detail="Winkeltoewijzing geldt alleen voor leden, niet voor de eigenaar."
            )
        for store_id in verzoek.winkel_ids:
            if not db_winkels.hoort_store_bij_organisatie(tenants_db, store_id, eigenaar.organisatie_id):
                statuscode = 422
                raise HTTPException(status_code=422, detail=f"Onbekend store_id: {store_id}")

        db_gebruiker_winkels.stel_toewijzingen_in(
            tenants_db, gebruiker_id=gebruiker_id, extern_store_ids=verzoek.winkel_ids
        )
        statuscode = 200
    finally:
        audit.log(
            settings.audit_log_file,
            {
                "key": eigenaar.email,
                "organisatie_id": eigenaar.organisatie_id,
                "doel_gebruiker_id": gebruiker_id,
                "winkel_ids": verzoek.winkel_ids,
                "statuscode": statuscode,
                "latency_ms": round((time.monotonic() - start) * 1000, 1),
            },
            versleuteld=settings.encrypt_at_rest,
        )

    winkel_ids = db_gebruiker_winkels.lijst_toegewezen_winkels(tenants_db, gebruiker_id=gebruiker_id)
    return WinkelToewijzingResponse(winkel_ids=winkel_ids)


@app.get("/organisatie/instellingen", response_model=OrganisatieInstellingenResponse)
def organisatie_instellingen_lezen(
    gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie),
) -> OrganisatieInstellingenResponse:
    # Leesbaar voor elke ingelogde gebruiker (niet alleen eigenaar-only
    # zoals het wijzigen): een lid heeft de prijs nodig om het herbestel-
    # advies op /forecast te kunnen zien. De prijs zelf is geen geheim.
    prijs = db_organisaties.haal_gemiddelde_omzet_per_stuk(tenants_db, organisatie_id=gebruiker.organisatie_id)
    return OrganisatieInstellingenResponse(gemiddelde_omzet_per_stuk=prijs)


@app.put("/organisatie/instellingen", response_model=OrganisatieInstellingenResponse)
def organisatie_instellingen_instellen(
    verzoek: OrganisatieInstellingenVerzoek, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)
) -> OrganisatieInstellingenResponse:
    db_organisaties.stel_gemiddelde_omzet_per_stuk_in(
        tenants_db, organisatie_id=eigenaar.organisatie_id, bedrag=verzoek.gemiddelde_omzet_per_stuk
    )
    return OrganisatieInstellingenResponse(gemiddelde_omzet_per_stuk=verzoek.gemiddelde_omzet_per_stuk)


@app.get("/organisatie/verkoopdata", response_model=VerkoopdataResponse)
def verkoopdata_lezen(gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)) -> VerkoopdataResponse:
    # Leesbaar voor elke ingelogde gebruiker, net als de herbestel-prijs —
    # alleen het uploaden (wijzigen) is eigenaar-only.
    rijen = db_verkoopdata.haal_verkoopdata(tenants_db, organisatie_id=gebruiker.organisatie_id)
    return VerkoopdataResponse(rijen=[VerkoopdataRij(**r) for r in rijen])


@app.post("/organisatie/verkoopdata", response_model=VerkoopdataUploadResponse)
def verkoopdata_uploaden(
    bestand: UploadFile, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)
) -> VerkoopdataUploadResponse:
    inhoud = bestand.file.read().decode("utf-8", errors="replace")
    try:
        rijen = parse_verkoopdata_csv(inhoud)
    except OngeldigeVerkoopdata as e:
        raise HTTPException(status_code=422, detail=str(e))
    db_verkoopdata.vervang_verkoopdata(tenants_db, organisatie_id=eigenaar.organisatie_id, rijen=rijen)
    return VerkoopdataUploadResponse(aantal_rijen=len(rijen))


@app.get("/organisatie/eigen-voorspelling", response_model=EigenVoorspellingResponse)
def eigen_voorspelling_lezen(
    horizon_dagen: int = Query(7, gt=0), gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)
) -> EigenVoorspellingResponse:
    """Voorspelling op basis van de eigen geüploade verkoopdata, voor
    organisaties zonder winkel in het gedeelde model (elke self-serve
    signup) — zie serving/eigen_voorspelling.py. Leesbaar voor elke
    ingelogde gebruiker, net als /organisatie/verkoopdata zelf."""
    rijen = db_verkoopdata.haal_verkoopdata(tenants_db, organisatie_id=gebruiker.organisatie_id)
    if len(rijen) < MINIMUM_DAGEN:
        return EigenVoorspellingResponse(beschikbaar=False, dagen_verzameld=len(rijen), dagen_nodig=MINIMUM_DAGEN)

    resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=horizon_dagen, vanaf=date.today())
    prijs = db_organisaties.haal_gemiddelde_omzet_per_stuk(tenants_db, organisatie_id=gebruiker.organisatie_id)
    advies = herbestel_advies(resultaat["totaal_p10"], resultaat["totaal_p50"], resultaat["totaal_p90"], prijs)
    return EigenVoorspellingResponse(
        beschikbaar=True, dagen_verzameld=len(rijen), dagen_nodig=MINIMUM_DAGEN,
        voorspellingen=[EigenVoorspellingDag(**v) for v in resultaat["voorspellingen"]],
        totaal_p10=resultaat["totaal_p10"], totaal_p50=resultaat["totaal_p50"], totaal_p90=resultaat["totaal_p90"],
        herbestel_advies=HerbestelAdvies(**advies) if advies else None,
    )


@app.post("/organisatie/product-verkoopdata", response_model=ProductVerkoopdataUploadResponse)
def product_verkoopdata_uploaden(
    bestand: UploadFile, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)
) -> ProductVerkoopdataUploadResponse:
    # Herbestel-advies per product is een premium-functie (zelfde reden
    # als self-serve API-keys hierboven) — nooit beschikbaar tijdens de
    # proefperiode.
    if db_organisaties.is_in_proefperiode(tenants_db, eigenaar.organisatie_id):
        raise HTTPException(
            status_code=403,
            detail="Herbestel-advies per product is een premium-functie, niet beschikbaar in je proefperiode.",
        )
    inhoud = bestand.file.read().decode("utf-8", errors="replace")
    try:
        rijen = parse_product_verkoopdata_csv(inhoud)
    except OngeldigeProductVerkoopdata as e:
        raise HTTPException(status_code=422, detail=str(e))
    db_product_verkoopdata.vervang_product_verkoopdata(tenants_db, organisatie_id=eigenaar.organisatie_id, rijen=rijen)
    return ProductVerkoopdataUploadResponse(aantal_rijen=len(rijen))


@app.get("/organisatie/herbestel-advies-per-product", response_model=ProductHerbestelAdviesResponse)
def herbestel_advies_per_product_lezen(
    horizon_dagen: int = Query(7, gt=0), gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)
) -> ProductHerbestelAdviesResponse:
    """Leesbaar voor elke ingelogde gebruiker, net als /organisatie/
    eigen-voorspelling — alleen het uploaden is eigenaar-only."""
    if db_organisaties.is_in_proefperiode(tenants_db, gebruiker.organisatie_id):
        raise HTTPException(
            status_code=403,
            detail="Herbestel-advies per product is een premium-functie, niet beschikbaar in je proefperiode.",
        )
    rijen = db_product_verkoopdata.haal_product_verkoopdata(tenants_db, organisatie_id=gebruiker.organisatie_id)
    items = bereken_herbestel_advies_per_product(rijen, horizon_dagen=horizon_dagen, vanaf=date.today())
    return ProductHerbestelAdviesResponse(items=items)


@app.post("/api-keys", response_model=NieuweApiKeyResponse, status_code=201)
def api_key_aanmaken(
    verzoek: ApiKeyAanmakenVerzoek, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)
) -> NieuweApiKeyResponse:
    # Premium-functie: zelf API-keys aanmaken hoort niet bij de gratis
    # proefperiode, zie de trial/premium-fundament-beslissing.
    if db_organisaties.is_in_proefperiode(tenants_db, eigenaar.organisatie_id):
        raise HTTPException(
            status_code=403,
            detail="Zelfbediening API-keys is een premium-functie, niet beschikbaar in je proefperiode.",
        )
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

        # Winkeltoewijzing (portfolio-dashboard item 10): alleen voor een
        # ingelogde "lid"-sessie. Zelfde 404-redenering als hierboven — de
        # winkel bestaat wel binnen de organisatie, maar dat mag dit lid
        # niet kunnen afleiden uit het verschil tussen 403 en 404.
        if key.rol == "lid" and not db_gebruiker_winkels.hoort_winkel_bij_toewijzing(
            tenants_db, gebruiker_id=key.gebruiker_id, extern_store_id=verzoek.store_id
        ):
            statuscode = 404
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

        # Promotie/schoolvakantie-invoer is een premium-functie: tijdens de
        # proefperiode stilzwijgend negeren (geen foutcode — dit zijn
        # optionele verrijkingsvelden op een verder werkend verzoek, geen
        # losse actie zoals API-key aanmaken). Verdediging in de diepte:
        # de frontend toont deze velden al uitgeschakeld tijdens de trial.
        in_proefperiode = db_organisaties.is_in_proefperiode(tenants_db, key.organisatie_id)
        resultaat = voorspel_periode(
            modellen=artefact["modellen"],
            historie=artefact["historie"],
            winkel_metadata=artefact["winkel_metadata"],
            store_id=verzoek.store_id,
            start_datum=verzoek.start_datum,
            horizon_dagen=verzoek.horizon_dagen,
            promo_datums=set() if in_proefperiode else dagreeks(verzoek.promo_van, verzoek.promo_tot),
            schoolvakantie_datums=(
                set() if in_proefperiode else dagreeks(verzoek.schoolvakantie_van, verzoek.schoolvakantie_tot)
            ),
            verklaar=True,
        )
        vorige_omzet = vorige_periode_omzet(
            historie=artefact["historie"], store_id=verzoek.store_id,
            start_datum=verzoek.start_datum, horizon_dagen=verzoek.horizon_dagen,
        )
        gemiddelde_prijs = db_organisaties.haal_gemiddelde_omzet_per_stuk(
            tenants_db, organisatie_id=key.organisatie_id
        )
        advies = herbestel_advies(
            totaal_p10=float(resultaat.voorspellingen["p10"].sum()),
            totaal_p50=float(resultaat.voorspellingen["p50"].sum()),
            totaal_p90=float(resultaat.voorspellingen["p90"].sum()),
            gemiddelde_omzet_per_stuk=gemiddelde_prijs,
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
        vorige_periode_omzet=vorige_omzet,
        herbestel_advies=HerbestelAdvies(**advies) if advies else None,
    )


@app.get("/voorbeeld/forecast", response_model=ForecastResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def voorbeeld_forecast(
    request: Request, gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)
) -> ForecastResponse:
    # Bewust NOOIT tenant-geïsoleerd — geen db_winkels/hoort_store_bij_
    # organisatie-check, in tegenstelling tot POST /forecast hierboven. Dit
    # is geen versoepelde variant van die controle, maar een apart pad
    # ernaast: een self-serve organisatie heeft nooit een eigen
    # winkelbinding (zie FASE4-SAAS-FOUNDATION.md beslissing 4) en heeft
    # minimaal MINIMUM_DAGEN dagen eigen data nodig vóór de eigen
    # voorspelling iets teruggeeft — zonder dit voorbeeld zou zo'n
    # organisatie wekenlang nooit een werkende voorspelling zien.
    start = time.monotonic()
    statuscode = 500
    horizon_dagen = 14
    try:
        if settings.voorbeeld_store_id is None:
            statuscode = 503
            raise HTTPException(status_code=503, detail="Voorbeeldvoorspelling is nog niet geconfigureerd.")

        gevalideerde_horizon = artefact["metadata"]["gevalideerde_horizon_dagen"]
        if horizon_dagen > gevalideerde_horizon:
            statuscode = 503
            raise HTTPException(status_code=503, detail="Voorbeeldvoorspelling is momenteel niet beschikbaar.")

        start_datum = pd.Timestamp(artefact["metadata"]["trainingsperiode_eind"][:10]) + pd.Timedelta(days=1)
        try:
            resultaat = voorspel_periode(
                modellen=artefact["modellen"],
                historie=artefact["historie"],
                winkel_metadata=artefact["winkel_metadata"],
                store_id=settings.voorbeeld_store_id,
                start_datum=start_datum,
                horizon_dagen=horizon_dagen,
                verklaar=False,
            )
        except (OnbekendeWinkel, HorizonBuitenBereik):
            statuscode = 503
            raise HTTPException(status_code=503, detail="Voorbeeldvoorspelling is momenteel niet beschikbaar.")

        statuscode = 200
        return ForecastResponse(
            store_id=settings.voorbeeld_store_id,
            voorspellingen=[
                DagVoorspelling(datum=rij["Date"].date(), p10=rij["p10"], p50=rij["p50"], p90=rij["p90"])
                for _, rij in resultaat.voorspellingen.iterrows()
            ],
            belangrijkste_factoren=[],
            vorige_periode_omzet=None,
            herbestel_advies=None,
        )
    finally:
        audit.log(
            settings.audit_log_file,
            {
                "gebruiker": gebruiker.email,
                "organisatie_id": gebruiker.organisatie_id,
                "store_id": settings.voorbeeld_store_id,
                "statuscode": statuscode,
                "latency_ms": round((time.monotonic() - start) * 1000, 1),
            },
            versleuteld=settings.encrypt_at_rest,
        )


@app.get("/metrics", response_model=MetricsResponse)
def metrics(key: GeauthenticeerdeKey = Depends(vereis_toegang)) -> MetricsResponse:
    m = artefact["metadata"]
    # Laatste 10 versies: genoeg om een trend te tonen zonder dat het
    # overzicht blijft groeien naarmate er meer versies bijkomen.
    geschiedenis = lijst_metadata_per_versie(settings.models_dir, versleuteld=settings.encrypt_at_rest)[-10:]
    return MetricsResponse(
        model_versie=m["versie"],
        rmspe=m["metrics"]["rmspe"],
        coverage_p10_p90=m["metrics"]["coverage_p10_p90"],
        n_observaties=m["metrics"]["n_observaties"],
        gevalideerde_horizon_dagen=m["gevalideerde_horizon_dagen"],
        trainingsperiode_eind=m["trainingsperiode_eind"][:10],
        geschiedenis=[ModelVersieMetric(**g) for g in geschiedenis],
    )


@app.get("/winkels", response_model=list[WinkelResponse])
def winkels_lijst(key: GeauthenticeerdeKey = Depends(vereis_toegang)) -> list[WinkelResponse]:
    rijen = db_winkels.lijst_winkels(tenants_db, organisatie_id=key.organisatie_id)
    if key.rol == "lid":
        toegewezen = set(db_gebruiker_winkels.lijst_toegewezen_winkels(tenants_db, gebruiker_id=key.gebruiker_id))
        rijen = [r for r in rijen if r.extern_store_id in toegewezen]
    return [WinkelResponse(extern_store_id=r.extern_store_id, naam=r.naam) for r in rijen]


@app.get("/portfolio", response_model=PortfolioResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def portfolio(
    request: Request,
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
    if key.rol == "lid":
        toegewezen = set(db_gebruiker_winkels.lijst_toegewezen_winkels(tenants_db, gebruiker_id=key.gebruiker_id))
        alle_winkels = [r for r in alle_winkels if r.extern_store_id in toegewezen]
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
