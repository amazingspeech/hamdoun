import numpy as np
import pandas as pd
import pytest

from training import train


def _synthetische_trainset(n=300):
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "Store": rng.integers(1, 4, n),
        "DayOfWeek": rng.integers(1, 8, n),
        "Promo": rng.integers(0, 2, n),
        "SchoolHoliday": rng.integers(0, 2, n),
        "Jaar": 2015,
        "Maand": rng.integers(1, 13, n),
        "Dag": rng.integers(1, 28, n),
        "Weeknummer": rng.integers(1, 53, n),
        "CompetitionDistance": rng.uniform(100, 5000, n),
        "omzet_lag_7": rng.uniform(500, 2000, n),
        "omzet_lag_14": rng.uniform(500, 2000, n),
        "omzet_lag_21": rng.uniform(500, 2000, n),
        "omzet_rolling_gemiddeld_7": rng.uniform(500, 2000, n),
        "omzet_rolling_gemiddeld_28": rng.uniform(500, 2000, n),
        "Open": 1,
    })
    df["Sales"] = df["omzet_rolling_gemiddeld_7"] + rng.normal(0, 50, n)
    return df


def test_bereid_trainset_voor_verwijdert_onvolledige_rijen():
    df = _synthetische_trainset(20)
    df.loc[0, "omzet_lag_7"] = np.nan
    resultaat = train.bereid_trainset_voor(df)
    assert len(resultaat) == 19


def test_bereid_trainset_voor_verwijdert_gesloten_winkeldagen():
    df = _synthetische_trainset(20)
    df.loc[0, "Open"] = 0
    resultaat = train.bereid_trainset_voor(df)
    assert len(resultaat) == 19


def test_train_alle_kwantielen_faalt_hard_op_lege_trainset():
    lege_df = _synthetische_trainset(5)
    lege_df["Open"] = 0
    with pytest.raises(ValueError, match="leeg"):
        train.train_alle_kwantielen(lege_df)


def test_train_alle_kwantielen_geeft_drie_modellen():
    df = _synthetische_trainset(300)
    modellen = train.train_alle_kwantielen(df)
    assert set(modellen.keys()) == {0.1, 0.5, 0.9}


def test_getraind_model_geeft_eindige_voorspellingen():
    df = _synthetische_trainset(300)
    modellen = train.train_alle_kwantielen(df)
    voorspeld = modellen[0.5].predict(df[train.FEATURE_KOLOMMEN].iloc[:5])
    assert np.all(np.isfinite(voorspeld))
