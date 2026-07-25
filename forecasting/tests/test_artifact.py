import numpy as np
import pandas as pd
import pytest

from security import encryptie
from training import artifact, train


def _getraind_modellenset():
    n = 200
    rng = np.random.default_rng(0)
    df = pd.DataFrame({k: rng.uniform(0, 100, n) for k in train.FEATURE_KOLOMMEN})
    df["Sales"] = rng.uniform(500, 2000, n)
    df["Open"] = 1
    return train.train_alle_kwantielen(df)


def test_schrijf_en_laad_artefact_zonder_encryptie(tmp_path):
    modellen = _getraind_modellenset()
    historie = pd.DataFrame({
        "Store": [1, 1], "Date": pd.to_datetime(["2015-07-01", "2015-07-02"]),
        "Sales": [1000.0, 1100.0], "Open": [1, 1],
    })
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    metrics = {"rmspe": 0.12, "coverage_p10_p90": 0.81, "n_observaties": 1000}

    versie = artifact.schrijf_artefact(
        basis_map=tmp_path, modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        metrics=metrics, trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=48, versleuteld=False,
    )

    geladen = artifact.laad_artefact(tmp_path, versie)
    assert set(geladen["modellen"].keys()) == {0.1, 0.5, 0.9}
    assert geladen["historie"]["Sales"].tolist() == [1000.0, 1100.0]
    assert geladen["winkel_metadata"]["CompetitionDistance"].tolist() == [500.0]
    assert geladen["metadata"]["metrics"]["rmspe"] == 0.12
    assert geladen["metadata"]["gevalideerde_horizon_dagen"] == 48


def test_schrijf_en_laad_artefact_met_encryptie(tmp_path, monkeypatch):
    monkeypatch.setenv(encryptie.SLEUTEL_ENV_VAR, encryptie.genereer_sleutel())
    encryptie._sleutel_cache = None

    modellen = _getraind_modellenset()
    historie = pd.DataFrame({
        "Store": [1], "Date": pd.to_datetime(["2015-07-01"]), "Sales": [1000.0], "Open": [1],
    })
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    metrics = {"rmspe": 0.1, "coverage_p10_p90": 0.8, "n_observaties": 10}

    versie = artifact.schrijf_artefact(
        basis_map=tmp_path, modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        metrics=metrics, trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=48, versleuteld=True,
    )

    # rauwe bestandsinhoud mag geen leesbare JSON zijn
    ruwe_metadata = (tmp_path / versie / "metadata.json").read_bytes()
    assert ruwe_metadata.startswith(encryptie.MAGIC)

    geladen = artifact.laad_artefact(tmp_path, versie, versleuteld=True)
    assert geladen["metadata"]["metrics"]["rmspe"] == 0.1


def test_geschreven_bestanden_hebben_chmod_600(tmp_path):
    modellen = _getraind_modellenset()
    historie = pd.DataFrame({"Store": [1], "Date": pd.to_datetime(["2015-07-01"]), "Sales": [1000.0], "Open": [1]})
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    versie = artifact.schrijf_artefact(
        basis_map=tmp_path, modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.1, "coverage_p10_p90": 0.8, "n_observaties": 1},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=48, versleuteld=False,
    )
    for pad in (tmp_path / versie).iterdir():
        assert oct(pad.stat().st_mode)[-3:] == "600"


def test_laad_artefact_faalt_hard_bij_onbekende_versie(tmp_path):
    with pytest.raises(RuntimeError, match="bestaat niet"):
        artifact.laad_artefact(tmp_path, "geen-bestaande-versie")


def test_twee_snel_opeenvolgende_writes_krijgen_verschillende_versies(tmp_path, monkeypatch):
    modellen = _getraind_modellenset()
    historie = pd.DataFrame({"Store": [1], "Date": pd.to_datetime(["2015-07-01"]), "Sales": [1000.0], "Open": [1]})
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    monkeypatch.setattr(artifact, "nieuwe_versie_naam", lambda: "zelfde-tijdstip")

    versie_1 = artifact.schrijf_artefact(
        basis_map=tmp_path, modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.1, "coverage_p10_p90": 0.8, "n_observaties": 1},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=48, versleuteld=False,
    )
    versie_2 = artifact.schrijf_artefact(
        basis_map=tmp_path, modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.1, "coverage_p10_p90": 0.8, "n_observaties": 1},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=48, versleuteld=False,
    )
    assert versie_1 != versie_2


def test_bewaar_historie_beperkt_tot_buffer_venster():
    df = pd.DataFrame({
        "Store": [1] * 40,
        "Date": pd.date_range("2015-01-01", periods=40, freq="D"),
        "Sales": range(40),
        "Open": [1] * 40,
    })
    resultaat = artifact.bewaar_historie(df, tot_en_met=pd.Timestamp("2015-02-09"))
    verwachte_grens = pd.Timestamp("2015-02-09") - pd.Timedelta(days=artifact.HISTORIE_BUFFER_DAGEN)
    assert resultaat["Date"].min() > verwachte_grens
    assert resultaat["Date"].max() == pd.Timestamp("2015-02-09")


def test_bewaar_winkel_metadata_selecteert_juiste_kolommen():
    winkels = pd.DataFrame({
        "Store": [1, 2], "StoreType": ["a", "b"], "Assortment": ["a", "a"],
        "CompetitionDistance": [500.0, 1200.0],
    })
    resultaat = artifact.bewaar_winkel_metadata(winkels)
    assert list(resultaat.columns) == ["Store", "CompetitionDistance"]
