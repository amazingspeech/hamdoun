"""Inlezen en samenvoegen van de brondata, met expliciete afhandeling van
bekende dataquirks (zie design-spec, sectie Data & model)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

VERPLICHTE_TRAIN_KOLOMMEN = {
    "Store", "DayOfWeek", "Date", "Sales", "Customers",
    "Open", "Promo", "StateHoliday", "SchoolHoliday",
}
VERPLICHTE_STORE_KOLOMMEN = {
    "Store", "StoreType", "Assortment", "CompetitionDistance",
}


def laad_train(pad: Path) -> pd.DataFrame:
    """Leest train.csv. StateHoliday expliciet als string inlezen: het
    bestand mixt '0' (geen feestdag) met 'a'/'b'/'c' (feestdagtypes), en
    zonder dtype-hint leidt pandas hier soms een gemengd int/str-type uit
    af, wat verderop stille bugs geeft in de featureconstructie."""
    df = pd.read_csv(pad, dtype={"StateHoliday": str}, parse_dates=["Date"])
    ontbrekend = VERPLICHTE_TRAIN_KOLOMMEN - set(df.columns)
    if ontbrekend:
        raise ValueError(f"train.csv mist verplichte kolommen: {sorted(ontbrekend)}")
    return df.sort_values(["Store", "Date"]).reset_index(drop=True)


def laad_winkels(pad: Path) -> pd.DataFrame:
    df = pd.read_csv(pad)
    ontbrekend = VERPLICHTE_STORE_KOLOMMEN - set(df.columns)
    if ontbrekend:
        raise ValueError(f"store.csv mist verplichte kolommen: {sorted(ontbrekend)}")
    return df


def laad_test(pad: Path) -> pd.DataFrame:
    """Leest test.csv. Een klein aantal rijen mist de Open-waarde; die vullen
    we expliciet met 1 (open) — de aanname die de Rossmann-competitie zelf
    hanteert voor deze ontbrekende waarden. Nooit stilzwijgend als NaN laten
    doorlopen naar de featureconstructie."""
    df = pd.read_csv(pad, dtype={"StateHoliday": str}, parse_dates=["Date"])
    if "Open" in df.columns and df["Open"].isna().any():
        df["Open"] = df["Open"].fillna(1).astype(int)
    return df.sort_values(["Store", "Date"]).reset_index(drop=True)


def samenvoegen(transacties: pd.DataFrame, winkels: pd.DataFrame) -> pd.DataFrame:
    df = transacties.merge(winkels, on="Store", how="left", validate="many_to_one")
    ontbrekende_metadata = df["StoreType"].isna().sum()
    if ontbrekende_metadata:
        raise ValueError(
            f"{ontbrekende_metadata} rijen hebben geen winkelmetadata na de merge — "
            "controleer of store.csv alle Store-ID's uit de transacties bevat."
        )
    return df
