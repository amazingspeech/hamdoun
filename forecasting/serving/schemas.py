"""Pydantic-schema's voor de forecasting-API. De horizon-vs-gevalideerde-
periode-controle staat bewust niet hier — die vereist het geladen
modelartefact, dat pas bij de endpoint-handler bekend is (zie serving/app.py)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ForecastVerzoek(BaseModel):
    store_id: int = Field(..., gt=0)
    start_datum: date
    horizon_dagen: int = Field(..., gt=0)
    # Optioneel: geplande promotie-/schoolvakantieperiode binnen de horizon.
    # Zonder opgave blijft het gedrag zoals voorheen (elke dag telt als
    # "geen promotie, geen schoolvakantie") — zie serving/forecast.py's
    # dagreeks() voor hoe dit wordt omgezet naar losse dagen.
    promo_van: Optional[date] = None
    promo_tot: Optional[date] = None
    schoolvakantie_van: Optional[date] = None
    schoolvakantie_tot: Optional[date] = None


class DagVoorspelling(BaseModel):
    datum: date
    p10: float
    p50: float
    p90: float


class FactorBijdrage(BaseModel):
    naam: str
    richting: Literal["hoger", "lager"]


class ForecastResponse(BaseModel):
    store_id: int
    voorspellingen: list[DagVoorspelling]
    belangrijkste_factoren: list[FactorBijdrage] = []


class LoginVerzoek(BaseModel):
    email: str
    wachtwoord: str = Field(..., min_length=1)


class GebruikerAanmakenVerzoek(BaseModel):
    email: str
    wachtwoord: str = Field(..., min_length=1)


class GebruikerResponse(BaseModel):
    id: int
    email: str
    rol: str
    actief: bool


class ApiKeyAanmakenVerzoek(BaseModel):
    naam: str = Field(..., min_length=1)


class ApiKeyResponse(BaseModel):
    id: int
    naam: str
    actief: bool
    aangemaakt_op: datetime


class NieuweApiKeyResponse(BaseModel):
    id: int
    naam: str
    ruwe_key: str


class MetricsResponse(BaseModel):
    model_versie: str
    rmspe: float
    coverage_p10_p90: float
    n_observaties: int
    gevalideerde_horizon_dagen: int
    trainingsperiode_eind: date
