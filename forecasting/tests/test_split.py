import pandas as pd

from pipeline import split


def _dataset(n_dagen=100):
    datums = pd.date_range("2015-01-01", periods=n_dagen, freq="D")
    return pd.DataFrame({"Store": 1, "Date": datums, "Sales": range(n_dagen)})


def test_split_grenzen_kloppen():
    df = _dataset(100)
    train, validatie, test = split.walk_forward_split(df, validatie_dagen=10, test_dagen=10)
    assert train["Date"].max() < validatie["Date"].min()
    assert validatie["Date"].max() < test["Date"].min()
    assert test["Date"].max() == df["Date"].max()


def test_split_dagaantallen_kloppen():
    df = _dataset(100)
    train, validatie, test = split.walk_forward_split(df, validatie_dagen=10, test_dagen=10)
    assert len(test) == 10
    assert len(validatie) == 10
    assert len(train) == 80


def test_split_geen_overlap_tussen_sets():
    df = _dataset(60)
    train, validatie, test = split.walk_forward_split(df, validatie_dagen=7, test_dagen=7)
    alle_datums = pd.concat([train["Date"], validatie["Date"], test["Date"]])
    assert alle_datums.is_unique
    assert len(alle_datums) == len(df)
