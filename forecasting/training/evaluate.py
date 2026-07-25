"""Evaluatie: RMSPE (met expliciete uitsluiting van nul-omzetdagen) en
coverage van de p10-p90-band."""
from __future__ import annotations

import numpy as np
import pandas as pd

from training.train import DOEL_KOLOM, FEATURE_KOLOMMEN


def rmspe(werkelijk: pd.Series, voorspeld: pd.Series) -> float:
    """Root Mean Squared Percentage Error, met dagen waarop de werkelijke
    omzet 0 is expliciet uitgesloten — anders deling door nul. De officiële
    Rossmann-competitiemetriek, dus vergelijkbaar met gepubliceerde
    benchmarks."""
    masker = werkelijk != 0
    if not masker.any():
        raise ValueError("Geen enkele rij met werkelijke omzet != 0 — kan RMSPE niet berekenen.")
    fout_percentage = (werkelijk[masker] - voorspeld[masker]) / werkelijk[masker]
    return float(np.sqrt(np.mean(np.square(fout_percentage))))


def coverage(werkelijk: pd.Series, p10: pd.Series, p90: pd.Series) -> float:
    """Aandeel werkelijke waarden dat binnen de p10-p90-band valt. Nominaal
    ~0.80 voor een goed gekalibreerd kwantielmodel — zonder deze check is de
    onzekerheidsband een ongefundeerde claim."""
    binnen_band = (werkelijk >= p10) & (werkelijk <= p90)
    return float(binnen_band.mean())


def sorteer_kwantielen(
    p10: np.ndarray, p50: np.ndarray, p90: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Drie onafhankelijk getrainde kwantielmodellen garanderen niet dat
    p10 <= p50 <= p90 per rij. Sorteert de drie waarden per rij zodat de
    teruggegeven band altijd logisch geordend is."""
    gestapeld = np.stack([p10, p50, p90], axis=0)
    gesorteerd = np.sort(gestapeld, axis=0)
    return gesorteerd[0], gesorteerd[1], gesorteerd[2]


def evalueer(modellen: dict[float, object], testset: pd.DataFrame) -> dict:
    voorbereid = testset.dropna(subset=FEATURE_KOLOMMEN + [DOEL_KOLOM])
    voorbereid = voorbereid[voorbereid["Open"] == 1]
    if voorbereid.empty:
        raise ValueError("Testset is leeg na filtering — kan niet evalueren.")

    ruwe_p10 = modellen[0.1].predict(voorbereid[FEATURE_KOLOMMEN])
    ruwe_p50 = modellen[0.5].predict(voorbereid[FEATURE_KOLOMMEN])
    ruwe_p90 = modellen[0.9].predict(voorbereid[FEATURE_KOLOMMEN])
    p10, p50, p90 = sorteer_kwantielen(ruwe_p10, ruwe_p50, ruwe_p90)

    return {
        "rmspe": rmspe(voorbereid[DOEL_KOLOM], pd.Series(p50, index=voorbereid.index)),
        "coverage_p10_p90": coverage(
            voorbereid[DOEL_KOLOM], pd.Series(p10, index=voorbereid.index), pd.Series(p90, index=voorbereid.index)
        ),
        "n_observaties": int(len(voorbereid)),
    }
