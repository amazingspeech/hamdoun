import numpy as np
import pandas as pd
import pytest

from training import evaluate


def test_rmspe_bekend_geval():
    werkelijk = pd.Series([100.0, 200.0])
    voorspeld = pd.Series([110.0, 180.0])
    # fouten: -10% en +10% -> sqrt(mean([0.01, 0.01])) = 0.1
    assert evaluate.rmspe(werkelijk, voorspeld) == pytest.approx(0.1, abs=1e-9)


def test_rmspe_sluit_nul_omzet_uit():
    werkelijk = pd.Series([0.0, 100.0])
    voorspeld = pd.Series([999.0, 110.0])
    # zonder de nul-rij uit te sluiten zou dit een ZeroDivisionError/inf geven
    resultaat = evaluate.rmspe(werkelijk, voorspeld)
    assert np.isfinite(resultaat)
    assert resultaat == pytest.approx(0.1, abs=1e-9)


def test_rmspe_faalt_hard_als_alles_nul_is():
    with pytest.raises(ValueError, match="RMSPE"):
        evaluate.rmspe(pd.Series([0.0, 0.0]), pd.Series([1.0, 2.0]))


def test_coverage_alles_binnen_band():
    werkelijk = pd.Series([5.0, 15.0, 25.0])
    p10 = pd.Series([0.0, 10.0, 20.0])
    p90 = pd.Series([10.0, 20.0, 30.0])
    assert evaluate.coverage(werkelijk, p10, p90) == pytest.approx(1.0)


def test_coverage_gedeeltelijk_buiten_band():
    werkelijk = pd.Series([5.0, 15.0, 35.0])
    p10 = pd.Series([0.0, 10.0, 20.0])
    p90 = pd.Series([10.0, 20.0, 30.0])
    assert evaluate.coverage(werkelijk, p10, p90) == pytest.approx(2 / 3)


def test_sorteer_kwantielen_corrigeert_kruising():
    p10, p50, p90 = evaluate.sorteer_kwantielen(
        np.array([50.0]), np.array([30.0]), np.array([70.0])
    )
    assert (p10[0], p50[0], p90[0]) == (30.0, 50.0, 70.0)


def test_sorteer_kwantielen_laat_correcte_volgorde_ongemoeid():
    p10, p50, p90 = evaluate.sorteer_kwantielen(
        np.array([10.0, 20.0]), np.array([50.0, 60.0]), np.array([90.0, 100.0])
    )
    assert list(p10) == [10.0, 20.0]
    assert list(p50) == [50.0, 60.0]
    assert list(p90) == [90.0, 100.0]


class _NepModel:
    def __init__(self, waarde):
        self.waarde = waarde

    def predict(self, X):
        return np.full(len(X), self.waarde)


def test_evalueer_geeft_rmspe_coverage_en_aantal():
    testset = pd.DataFrame({
        **{k: [1, 2, 3] for k in evaluate.FEATURE_KOLOMMEN if k != "Store"},
        "Store": [1, 1, 1],
        "Open": [1, 1, 1],
        evaluate.DOEL_KOLOM: [100.0, 100.0, 100.0],
    })
    modellen = {0.1: _NepModel(80.0), 0.5: _NepModel(100.0), 0.9: _NepModel(120.0)}
    resultaat = evaluate.evalueer(modellen, testset)
    assert resultaat["rmspe"] == pytest.approx(0.0, abs=1e-9)
    assert resultaat["coverage_p10_p90"] == pytest.approx(1.0)
    assert resultaat["n_observaties"] == 3
