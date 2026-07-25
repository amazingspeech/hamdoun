"""Voorspellingslogica: reconstrueert features uit de gebundelde historie en
roept de drie kwantielmodellen aan.

Voorspelt recursief: elke volgende dag gebruikt de p50-voorspelling van
eerder voorspelde dagen als werkwaarde voor de lag-/rolling-features. Dit is
nodig omdat de gevalideerde horizon (tot 48 dagen) de langste lag (21 dagen)
kan overschrijden — de werkelijke omzet van een nog niet aangebroken dag is
per definitie onbekend. Compounding van fouten over een langere horizon is
een bekende, geaccepteerde beperking van deze aanpak (zie
KNOWN-LIMITATIONS.md). Hergebruikt dezelfde featurefuncties als tijdens
training, zodat serving-tijd-features nooit op een subtiel andere manier
worden berekend dan trainings-tijd-features."""
from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline.features import voeg_kalenderfeatures_toe, voeg_lag_features_toe
from training.evaluate import sorteer_kwantielen
from training.train import FEATURE_KOLOMMEN


class OnbekendeWinkel(Exception):
    pass


class HorizonBuitenBereik(Exception):
    pass


def voorspel_periode(
    modellen: dict[float, object],
    historie: pd.DataFrame,
    winkel_metadata: pd.DataFrame,
    store_id: int,
    start_datum: pd.Timestamp,
    horizon_dagen: int,
) -> pd.DataFrame:
    if store_id not in historie["Store"].unique():
        raise OnbekendeWinkel(f"Onbekend store_id: {store_id}")

    start_datum = pd.Timestamp(start_datum)
    # Preserve all input columns from history, filtering to the requested store
    store_history = historie[historie["Store"] == store_id].copy()
    # Ensure we have the essential columns; if missing from input, they'll be NaN and raise HorizonBuitenBereik
    essential_cols = ["Store", "Date", "Sales", "Open"]
    werkreeks = store_history[essential_cols].copy()
    # Preserve DayOfWeek, Promo, SchoolHoliday if they exist in the input
    for col in ["DayOfWeek", "Promo", "SchoolHoliday"]:
        if col in store_history.columns:
            werkreeks[col] = store_history[col].values
    resultaten = []

    for i in range(horizon_dagen):
        doel_datum = start_datum + pd.Timedelta(days=i)
        nieuwe_rij = pd.DataFrame({
            "Store": [store_id], "Date": [doel_datum], "Sales": [np.nan], "Open": [1],
            "DayOfWeek": [doel_datum.dayofweek + 1],
            "Promo": [0],  # Future promo status unknown; default to 0
            "SchoolHoliday": [0],  # Future school holiday status unknown; default to 0
        })
        volledig = pd.concat([werkreeks, nieuwe_rij], ignore_index=True)
        volledig = voeg_kalenderfeatures_toe(volledig)
        volledig = voeg_lag_features_toe(volledig)
        volledig = volledig.merge(winkel_metadata, on="Store", how="left")

        feature_rij = volledig.iloc[[-1]]
        if feature_rij[FEATURE_KOLOMMEN].isna().any(axis=1).iloc[0]:
            raise HorizonBuitenBereik(
                f"Onvoldoende historie om {doel_datum.date()} te voorspellen voor winkel {store_id}."
            )

        ruwe = {q: float(modellen[q].predict(feature_rij[FEATURE_KOLOMMEN])[0]) for q in (0.1, 0.5, 0.9)}
        p10, p50, p90 = sorteer_kwantielen(
            np.array([ruwe[0.1]]), np.array([ruwe[0.5]]), np.array([ruwe[0.9]])
        )
        resultaten.append({"Date": doel_datum, "p10": float(p10[0]), "p50": float(p50[0]), "p90": float(p90[0])})

        werkreeks = pd.concat(
            [werkreeks, pd.DataFrame({"Store": [store_id], "Date": [doel_datum], "Sales": [float(p50[0])], "Open": [1]})],
            ignore_index=True,
        )

    return pd.DataFrame(resultaten)
