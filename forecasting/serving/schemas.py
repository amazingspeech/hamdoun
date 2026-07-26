"""Pydantic-schema's voor de forecasting-API. De horizon-vs-gevalideerde-
periode-controle staat bewust niet hier — die vereist het geladen
modelartefact, dat pas bij de endpoint-handler bekend is (zie serving/app.py)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ForecastVerzoek(BaseModel):
    store_id: int = Field(..., gt=0)
    start_datum: date
    horizon_dagen: int = Field(..., gt=0)


class DagVoorspelling(BaseModel):
    datum: date
    p10: float
    p50: float
    p90: float


class ForecastResponse(BaseModel):
    store_id: int
    voorspellingen: list[DagVoorspelling]


class LoginVerzoek(BaseModel):
    email: str
    wachtwoord: str = Field(..., min_length=1)


class MetricsResponse(BaseModel):
    model_versie: str
    rmspe: float
    coverage_p10_p90: float
    n_observaties: int
    gevalideerde_horizon_dagen: int
    trainingsperiode_eind: date
