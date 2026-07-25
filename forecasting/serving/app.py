"""FastAPI-app: dunne serving-laag, traint nooit zelf. Laadt bij import een
expliciet gepinde modelversie (MODEL_VERSION) — hard-fail als die ontbreekt
of niet bestaat, nooit een impliciet 'laatste' model."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from security import api_keys, audit
from serving.config import laad_settings
from serving.forecast import HorizonBuitenBereik, OnbekendeWinkel, voorspel_periode
from serving.schemas import DagVoorspelling, ForecastResponse, ForecastVerzoek, MetricsResponse
from training.artifact import laad_artefact

settings = laad_settings()
artefact = laad_artefact(settings.models_dir, settings.model_version, versleuteld=settings.encrypt_at_rest)


def _rate_limit_key(request: Request) -> str:
    """Rate-limit per API-key, niet per bron-IP: meerdere klantsystemen achter
    dezelfde NAT/proxy mogen niet dezelfde bucket delen. Valt terug op het
    IP-adres alleen als slowapi deze functie aanroept vóórdat
    vereis_api_key() draait (dus zonder geverifieerde key)."""
    return request.headers.get("X-API-Key") or get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)

app = FastAPI(title="Tessar Vraagvoorspelling")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def vereis_api_key(sleutel: Optional[str] = Security(api_key_header)) -> str:
    if not sleutel:
        raise HTTPException(status_code=401, detail="X-API-Key header ontbreekt.")
    naam = api_keys.vind_key_naam(settings.api_keys_file, sleutel)
    if naam is None:
        raise HTTPException(status_code=401, detail="Ongeldige API-key.")
    return naam


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_versie": settings.model_version}


@app.post("/forecast", response_model=ForecastResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def forecast(
    request: Request, verzoek: ForecastVerzoek, key_naam: str = Depends(vereis_api_key)
) -> ForecastResponse:
    gevalideerde_horizon = artefact["metadata"]["gevalideerde_horizon_dagen"]
    if verzoek.horizon_dagen > gevalideerde_horizon:
        raise HTTPException(
            status_code=422,
            detail=(
                f"horizon_dagen ({verzoek.horizon_dagen}) overschrijdt de tijdens training "
                f"gevalideerde periode ({gevalideerde_horizon} dagen)."
            ),
        )

    start = time.monotonic()
    statuscode = 500
    try:
        resultaat = voorspel_periode(
            modellen=artefact["modellen"],
            historie=artefact["historie"],
            winkel_metadata=artefact["winkel_metadata"],
            store_id=verzoek.store_id,
            start_datum=verzoek.start_datum,
            horizon_dagen=verzoek.horizon_dagen,
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
                "key": key_naam,
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
            for _, rij in resultaat.iterrows()
        ],
    )


@app.get("/metrics", response_model=MetricsResponse)
def metrics(key_naam: str = Depends(vereis_api_key)) -> MetricsResponse:
    m = artefact["metadata"]
    return MetricsResponse(
        model_versie=m["versie"],
        rmspe=m["metrics"]["rmspe"],
        coverage_p10_p90=m["metrics"]["coverage_p10_p90"],
        n_observaties=m["metrics"]["n_observaties"],
        gevalideerde_horizon_dagen=m["gevalideerde_horizon_dagen"],
    )


_dashboard_pad = Path(__file__).resolve().parent.parent / "dashboard"
if _dashboard_pad.exists():
    app.mount("/", StaticFiles(directory=str(_dashboard_pad), html=True), name="dashboard")
