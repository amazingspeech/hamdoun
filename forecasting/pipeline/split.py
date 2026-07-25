"""Tijd-geordende walk-forward split: nooit shufflen, dat zou data-lekkage
veroorzaken bij een tijdreeksprobleem."""
from __future__ import annotations

import pandas as pd

from pipeline.features import controleer_geen_lekkage


def walk_forward_split(
    df: pd.DataFrame, validatie_dagen: int, test_dagen: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Splitst df in train/validatie/test op basis van de laatste
    `validatie_dagen + test_dagen` kalenderdagen, niet op rijaantal — anders
    krijgen winkels met meer transacties een groter aandeel van de
    validatie-/testperiode dan winkels met minder."""
    laatste_datum = df["Date"].max()
    test_start = laatste_datum - pd.Timedelta(days=test_dagen - 1)
    validatie_start = test_start - pd.Timedelta(days=validatie_dagen)

    train = df[df["Date"] < validatie_start]
    validatie = df[(df["Date"] >= validatie_start) & (df["Date"] < test_start)]
    test = df[df["Date"] >= test_start]

    controleer_geen_lekkage(train, validatie)
    controleer_geen_lekkage(validatie, test)

    return train, validatie, test
