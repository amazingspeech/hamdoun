"""Traint p10/p50/p90-modellen via XGBoost quantile regression.

Vereist XGBoost >=2.0 voor objective='reg:quantileerror' (zie
requirements.in en README.md voor de LightGBM-terugval als dat in de
buildomgeving niet beschikbaar blijkt)."""
from __future__ import annotations

import pandas as pd
import xgboost as xgb

KWANTIELEN = (0.1, 0.5, 0.9)

FEATURE_KOLOMMEN = [
    "Store", "DayOfWeek", "Promo", "SchoolHoliday", "Jaar", "Maand", "Dag",
    "Weeknummer", "CompetitionDistance",
    "omzet_lag_7", "omzet_lag_14", "omzet_lag_21",
    "omzet_rolling_gemiddeld_7", "omzet_rolling_gemiddeld_28",
]
DOEL_KOLOM = "Sales"


def bereid_trainset_voor(df: pd.DataFrame) -> pd.DataFrame:
    """Verwijdert rijen zonder volledige laghistorie (begin van elke
    winkelreeks) en gesloten-winkeldagen — een gesloten winkel heeft per
    definitie omzet 0, geen zinvol trainingssignaal voor vraag bij open
    winkels."""
    volledig = df.dropna(subset=FEATURE_KOLOMMEN + [DOEL_KOLOM])
    return volledig[volledig["Open"] == 1]


def train_kwantielmodel(train_df: pd.DataFrame, kwantiel: float) -> xgb.XGBRegressor:
    model = xgb.XGBRegressor(
        objective="reg:quantileerror",
        quantile_alpha=kwantiel,
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        random_state=42,
    )
    model.fit(train_df[FEATURE_KOLOMMEN], train_df[DOEL_KOLOM])
    return model


def train_alle_kwantielen(train_df: pd.DataFrame) -> dict[float, xgb.XGBRegressor]:
    voorbereid = bereid_trainset_voor(train_df)
    if voorbereid.empty:
        raise ValueError("Trainset is leeg na het verwijderen van onvolledige/gesloten rijen.")
    return {q: train_kwantielmodel(voorbereid, q) for q in KWANTIELEN}
