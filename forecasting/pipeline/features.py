"""Featureconstructie voor het vraagvoorspellingsmodel.

Elke feature die uit het verleden van dezelfde winkel wordt afgeleid (lags,
rolling-gemiddeldes) moet strikt vóór de voorspeldatum liggen. groupby +
shift/transform garandeert dat een lag nooit de eigen rij (of een latere
rij), en nooit een andere winkel, gebruikt."""
from __future__ import annotations

import pandas as pd

LAG_DAGEN = (7, 14, 21)
ROLLING_VENSTERS = (7, 28)
MAX_HISTORIE_DAGEN = max(max(LAG_DAGEN), max(ROLLING_VENSTERS))


def voeg_kalenderfeatures_toe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Jaar"] = df["Date"].dt.year
    df["Maand"] = df["Date"].dt.month
    df["Dag"] = df["Date"].dt.day
    df["Weeknummer"] = df["Date"].dt.isocalendar().week.astype(int)
    return df


def voeg_lag_features_toe(df: pd.DataFrame) -> pd.DataFrame:
    """Voegt lag- en rolling-window-features toe, per winkel apart berekend.
    Rijen waarop de vereiste laghistorie ontbreekt (het begin van elke
    winkelreeks) krijgen NaN — die worden later expliciet uit de
    trainingsset verwijderd, niet stilzwijgend op 0 gezet."""
    df = df.sort_values(["Store", "Date"]).copy()
    for n in LAG_DAGEN:
        df[f"omzet_lag_{n}"] = df.groupby("Store")["Sales"].shift(n)
    for venster in ROLLING_VENSTERS:
        # .transform() garandeert output uitgelijnd met de originele index,
        # per groep berekend — voorkomt dat een rolling-window per ongeluk
        # over de grens van twee winkels heen kijkt.
        df[f"omzet_rolling_gemiddeld_{venster}"] = df.groupby("Store")["Sales"].transform(
            lambda s, w=venster: s.shift(1).rolling(w, min_periods=w).mean()
        )
    return df


def controleer_geen_lekkage(train: pd.DataFrame, validatie: pd.DataFrame) -> None:
    """Harde assertion: de trainingsperiode moet volledig vóór de
    validatieperiode liggen. Faalt de trainingsrun hard als dat niet zo is,
    in plaats van een opgeblazen nauwkeurigheidscijfer te laten ontstaan
    door toekomstige data die in de training is geslopen."""
    if train.empty or validatie.empty:
        raise ValueError("Train- of validatieset is leeg — kan lekkage niet controleren.")
    laatste_train_datum = train["Date"].max()
    eerste_validatie_datum = validatie["Date"].min()
    if laatste_train_datum >= eerste_validatie_datum:
        raise AssertionError(
            f"Data-lekkage: laatste trainingsdatum ({laatste_train_datum.date()}) ligt niet "
            f"vóór de eerste validatiedatum ({eerste_validatie_datum.date()})."
        )


def bouw_features(df: pd.DataFrame) -> pd.DataFrame:
    df = voeg_kalenderfeatures_toe(df)
    df = voeg_lag_features_toe(df)
    return df
