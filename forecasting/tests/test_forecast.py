from datetime import date

import numpy as np
import pandas as pd
import pytest

from serving.forecast import HorizonBuitenBereik, OnbekendeWinkel, dagreeks, voorspel_periode


class _NepModel:
    """Voorspelt altijd de rolling_gemiddeld_7-feature terug, zodat de test
    kan verifiëren dat features daadwerkelijk worden aangeleverd."""
    def predict(self, X):
        return X["omzet_rolling_gemiddeld_7"].to_numpy()


def _historie(store_id=1, n_dagen=40, basis=1000.0):
    datums = pd.date_range("2015-06-01", periods=n_dagen, freq="D")
    return pd.DataFrame({
        "Store": store_id, "Date": datums,
        "Sales": [basis + i for i in range(n_dagen)], "Open": 1,
        "DayOfWeek": [d.dayofweek + 1 for d in datums],
        "Promo": [i % 5 == 0 for i in range(n_dagen)],
        "SchoolHoliday": 0,
    })


def _winkel_metadata(store_id=1):
    return pd.DataFrame({"Store": [store_id], "CompetitionDistance": [500.0]})


def test_voorspel_periode_onbekende_winkel_raiset():
    with pytest.raises(OnbekendeWinkel):
        voorspel_periode(
            modellen={q: _NepModel() for q in (0.1, 0.5, 0.9)},
            historie=_historie(), winkel_metadata=_winkel_metadata(),
            store_id=999, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=3,
        )


def test_voorspel_periode_geeft_juiste_aantal_dagen():
    resultaat = voorspel_periode(
        modellen={q: _NepModel() for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        store_id=1, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=5,
    )
    assert len(resultaat) == 5
    assert list(resultaat.columns) == ["Date", "p10", "p50", "p90"]


def test_voorspel_periode_sorteert_gekruiste_kwantielen():
    class _GekruistModel:
        def __init__(self, waarde):
            self.waarde = waarde
        def predict(self, X):
            return np.full(len(X), self.waarde)

    # p10-model geeft een HOGERE waarde dan het p90-model -> moet gesorteerd worden
    modellen = {0.1: _GekruistModel(500.0), 0.5: _GekruistModel(300.0), 0.9: _GekruistModel(100.0)}
    resultaat = voorspel_periode(
        modellen=modellen, historie=_historie(), winkel_metadata=_winkel_metadata(),
        store_id=1, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=1,
    )
    rij = resultaat.iloc[0]
    assert rij["p10"] <= rij["p50"] <= rij["p90"]


def test_voorspel_periode_onvoldoende_historie_raiset():
    korte_historie = _historie(n_dagen=3)  # te weinig voor lag_7/lag_14/lag_21
    with pytest.raises(HorizonBuitenBereik):
        voorspel_periode(
            modellen={q: _NepModel() for q in (0.1, 0.5, 0.9)},
            historie=korte_historie, winkel_metadata=_winkel_metadata(),
            store_id=1, start_datum=pd.Timestamp("2015-06-05"), horizon_dagen=1,
        )


def test_voorspel_periode_werkt_voorbij_de_kortste_lag():
    # horizon_dagen=10 > lag_7 (7 dagen) -> vereist de recursieve stap
    resultaat = voorspel_periode(
        modellen={q: _NepModel() for q in (0.1, 0.5, 0.9)},
        historie=_historie(n_dagen=40), winkel_metadata=_winkel_metadata(),
        store_id=1, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=10,
    )
    assert len(resultaat) == 10
    assert resultaat["p50"].notna().all()


class _FeatureTeruggeefModel:
    """Geeft de gevraagde featurekolom letterlijk terug als 'voorspelling',
    zodat een test kan verifiëren welke waarde er daadwerkelijk als
    modelinvoer voor die dag is aangeleverd."""
    def __init__(self, kolom):
        self.kolom = kolom

    def predict(self, X):
        return X[self.kolom].to_numpy()


def test_voorspel_periode_gebruikt_opgegeven_promo_datums():
    resultaat = voorspel_periode(
        modellen={q: _FeatureTeruggeefModel("Promo") for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        store_id=1, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=3,
        promo_datums={pd.Timestamp("2015-07-12").date()},
    )
    assert resultaat.iloc[0]["p50"] == 0  # 11 juli: geen promo
    assert resultaat.iloc[1]["p50"] == 1  # 12 juli: wel promo
    assert resultaat.iloc[2]["p50"] == 0  # 13 juli: geen promo


def test_voorspel_periode_gebruikt_opgegeven_schoolvakantie_datums():
    resultaat = voorspel_periode(
        modellen={q: _FeatureTeruggeefModel("SchoolHoliday") for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        store_id=1, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=2,
        schoolvakantie_datums={pd.Timestamp("2015-07-11").date()},
    )
    assert resultaat.iloc[0]["p50"] == 1  # 11 juli: wel schoolvakantie
    assert resultaat.iloc[1]["p50"] == 0  # 12 juli: geen schoolvakantie


def test_voorspel_periode_zonder_opgegeven_datums_blijft_nul():
    resultaat = voorspel_periode(
        modellen={q: _FeatureTeruggeefModel("Promo") for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        store_id=1, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=1,
    )
    assert resultaat.iloc[0]["p50"] == 0


def test_dagreeks_zonder_van_geeft_lege_set():
    assert dagreeks(None, None) == set()


def test_dagreeks_alleen_van_geeft_één_dag():
    assert dagreeks(date(2015, 7, 12), None) == {date(2015, 7, 12)}


def test_dagreeks_van_tot_tot_geeft_inclusieve_reeks():
    assert dagreeks(date(2015, 7, 12), date(2015, 7, 14)) == {
        date(2015, 7, 12), date(2015, 7, 13), date(2015, 7, 14),
    }


def test_dagreeks_verwisselde_van_tot_wordt_gecorrigeerd():
    assert dagreeks(date(2015, 7, 14), date(2015, 7, 12)) == {
        date(2015, 7, 12), date(2015, 7, 13), date(2015, 7, 14),
    }
