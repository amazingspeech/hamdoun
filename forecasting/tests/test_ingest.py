import pandas as pd
import pytest

from pipeline import ingest


def _schrijf_csv(tmp_path, naam, inhoud):
    pad = tmp_path / naam
    pad.write_text(inhoud, encoding="utf-8")
    return pad


def test_laad_train_leest_stateholiday_als_string(tmp_path):
    pad = _schrijf_csv(
        tmp_path, "train.csv",
        "Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday\n"
        "1,1,2015-07-01,1000,200,1,1,0,0\n"
        "1,2,2015-07-02,1100,210,1,0,a,0\n",
    )
    df = ingest.laad_train(pad)
    assert df["StateHoliday"].dtype == object
    assert set(df["StateHoliday"]) == {"0", "a"}


def test_laad_train_faalt_hard_bij_ontbrekende_kolom(tmp_path):
    pad = _schrijf_csv(tmp_path, "train.csv", "Store,Date,Sales\n1,2015-07-01,1000\n")
    with pytest.raises(ValueError, match="mist verplichte kolommen"):
        ingest.laad_train(pad)


def test_laad_train_sorteert_op_winkel_en_datum(tmp_path):
    pad = _schrijf_csv(
        tmp_path, "train.csv",
        "Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday\n"
        "2,1,2015-07-01,500,100,1,0,0,0\n"
        "1,3,2015-07-03,1200,220,1,0,0,0\n"
        "1,1,2015-07-01,1000,200,1,1,0,0\n",
    )
    df = ingest.laad_train(pad)
    assert list(df["Store"]) == [1, 1, 2]
    assert list(df["Date"]) == list(pd.to_datetime(["2015-07-01", "2015-07-03", "2015-07-01"]))


def test_laad_test_vult_ontbrekende_open_met_1(tmp_path):
    pad = _schrijf_csv(
        tmp_path, "test.csv",
        "Store,DayOfWeek,Date,Open,Promo,StateHoliday,SchoolHoliday\n"
        "1,1,2015-08-01,,0,0,0\n"
        "1,2,2015-08-02,0,0,0,0\n",
    )
    df = ingest.laad_test(pad)
    assert df["Open"].tolist() == [1, 0]
    assert not df["Open"].isna().any()


def test_laad_winkels_faalt_hard_bij_ontbrekende_kolom(tmp_path):
    pad = _schrijf_csv(tmp_path, "store.csv", "Store,StoreType\n1,a\n")
    with pytest.raises(ValueError, match="mist verplichte kolommen"):
        ingest.laad_winkels(pad)


def test_samenvoegen_koppelt_winkelmetadata(tmp_path):
    transacties = pd.DataFrame({
        "Store": [1, 2], "DayOfWeek": [1, 1],
        "Date": pd.to_datetime(["2015-07-01", "2015-07-01"]),
        "Sales": [1000, 500], "Customers": [200, 100], "Open": [1, 1],
        "Promo": [0, 0], "StateHoliday": ["0", "0"], "SchoolHoliday": [0, 0],
    })
    winkels = pd.DataFrame({
        "Store": [1, 2], "StoreType": ["a", "b"], "Assortment": ["a", "a"],
        "CompetitionDistance": [500.0, 1200.0],
    })
    samengevoegd = ingest.samenvoegen(transacties, winkels)
    assert samengevoegd.loc[samengevoegd["Store"] == 1, "CompetitionDistance"].iloc[0] == 500.0


def test_samenvoegen_faalt_hard_bij_ontbrekende_winkelmetadata():
    transacties = pd.DataFrame({
        "Store": [1, 99], "DayOfWeek": [1, 1],
        "Date": pd.to_datetime(["2015-07-01", "2015-07-01"]),
        "Sales": [1000, 500], "Customers": [200, 100], "Open": [1, 1],
        "Promo": [0, 0], "StateHoliday": ["0", "0"], "SchoolHoliday": [0, 0],
    })
    winkels = pd.DataFrame({
        "Store": [1], "StoreType": ["a"], "Assortment": ["a"], "CompetitionDistance": [500.0],
    })
    with pytest.raises(ValueError, match="geen winkelmetadata"):
        ingest.samenvoegen(transacties, winkels)
