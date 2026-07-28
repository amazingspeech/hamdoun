import pandas as pd
import pytest

from pipeline import features


def _reeks(store, start, n, waarde_per_dag):
    datums = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({"Store": store, "Date": datums, "Sales": waarde_per_dag, "Open": 1})


def test_lag_feature_gebruikt_juiste_historische_waarde():
    df = pd.DataFrame({
        "Store": [1] * 10,
        "Date": pd.date_range("2015-01-01", periods=10, freq="D"),
        "Sales": list(range(100, 1100, 100)),
        "Open": [1] * 10,
    })
    resultaat = features.voeg_lag_features_toe(df)
    # dag 8 (index 7, Sales=800) moet als lag_7 de Sales van dag 1 (100) hebben
    assert resultaat.iloc[7]["omzet_lag_7"] == 100


def test_lag_feature_lekt_niet_tussen_winkels():
    df = pd.concat([
        _reeks(1, "2015-01-01", 10, 1000),
        _reeks(2, "2015-01-01", 10, 5000),
    ], ignore_index=True)
    resultaat = features.voeg_lag_features_toe(df)
    winkel_2_rijen = resultaat[resultaat["Store"] == 2]
    # de lag-waarden voor winkel 2 mogen nooit 1000 zijn (dat is winkel 1's omzet)
    assert not (winkel_2_rijen["omzet_lag_7"] == 1000).any()


def test_rolling_feature_respecteert_min_periods():
    df = _reeks(1, "2015-01-01", 5, 1000)
    resultaat = features.voeg_lag_features_toe(df)
    # venster van 7 dagen kan met maar 5 historische rijen nooit gevuld zijn
    assert resultaat["omzet_rolling_gemiddeld_7"].isna().all()


def test_rolling_feature_sluit_de_dag_zelf_uit():
    df = pd.DataFrame({
        "Store": [1] * 8,
        "Date": pd.date_range("2015-01-01", periods=8, freq="D"),
        "Sales": [100, 100, 100, 100, 100, 100, 100, 999999],
        "Open": [1] * 8,
    })
    resultaat = features.voeg_lag_features_toe(df)
    # rolling_7 op de laatste dag moet het gemiddelde zijn van de 7 dagen ervoor (allemaal 100),
    # niet beïnvloed door de 999999 van de dag zelf
    assert resultaat.iloc[-1]["omzet_rolling_gemiddeld_7"] == 100


def test_controleer_geen_lekkage_accepteert_correcte_scheiding():
    train = pd.DataFrame({"Date": pd.to_datetime(["2015-01-01", "2015-01-05"])})
    validatie = pd.DataFrame({"Date": pd.to_datetime(["2015-01-10"])})
    features.controleer_geen_lekkage(train, validatie)  # mag niet raisen


def test_controleer_geen_lekkage_verwerpt_overlap():
    train = pd.DataFrame({"Date": pd.to_datetime(["2015-01-01", "2015-01-15"])})
    validatie = pd.DataFrame({"Date": pd.to_datetime(["2015-01-10"])})
    with pytest.raises(AssertionError, match="lekkage"):
        features.controleer_geen_lekkage(train, validatie)


def test_controleer_geen_lekkage_verwerpt_lege_set():
    with pytest.raises(ValueError):
        features.controleer_geen_lekkage(pd.DataFrame({"Date": []}), pd.DataFrame({"Date": [pd.Timestamp("2015-01-01")]}))


def test_bouw_features_voegt_kalender_en_lag_toe():
    df = _reeks(1, "2015-01-01", 30, 1000)
    resultaat = features.bouw_features(df)
    for kolom in ("Jaar", "Maand", "Dag", "Weeknummer", "omzet_lag_7", "omzet_rolling_gemiddeld_28"):
        assert kolom in resultaat.columns
