"""GET /voorbeeld/forecast: een bewust nooit tenant-geïsoleerd
voorbeeld-eindpunt voor self-serve organisaties zonder eigen winkelbinding
of eigen data — zie forecasting/docs/superpowers/specs/2026-07-28-
self-serve-onboarding-design.md. Zelfde fixture-patroon als
test_eigen_voorspelling_endpoint.py."""
import importlib
import sys

from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database


def _bouw_omgeving(tmp_path, monkeypatch, voorbeeld_store_id="1"):
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")
    (tmp_path / "models").mkdir()

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)
    # Bewust store_ids=[] — dit bewijst dat het voorbeeld-eindpunt werkt
    # zonder dat de organisatie zelf ook maar één winkelbinding heeft.
    org_id = bootstrap_organisatie(engine, naam="Zelfbediening klant", slug="zelfbediening-klant", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@klant.nl", wachtwoord="een-goed-wachtwoord", rol="eigenaar")

    monkeypatch.setenv("MODEL_VERSION", _bootstrap_model(tmp_path))
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tenants_db_pad))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", "1000")
    monkeypatch.setenv("SESSIE_COOKIE_SECURE", "false")
    if voorbeeld_store_id is None:
        monkeypatch.delenv("VOORBEELD_STORE_ID", raising=False)
    else:
        monkeypatch.setenv("VOORBEELD_STORE_ID", voorbeeld_store_id)

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return TestClient(module.app)


def _bootstrap_model(tmp_path):
    import numpy as np
    import pandas as pd

    from training import artifact, train

    modellen = train.train_alle_kwantielen(pd.DataFrame({
        **{k: np.random.default_rng(1).uniform(0, 100, 200) for k in train.FEATURE_KOLOMMEN},
        "Sales": np.random.default_rng(1).uniform(500, 2000, 200),
        "Open": 1,
    }))
    # periods=30 (niet 40 zoals elders): historie moet exact eindigen op
    # trainingsperiode_eind (2015-06-30), net als training/cli.py dat in het
    # echt via bewaar_historie(tot_en_met=train_df["Date"].max()) altijd
    # doet. Met 40 dagen loopt historie 10 dagen door na trainingsperiode_
    # eind, wat voorspel_periode's start_datum (trainingsperiode_eind + 1)
    # middenin de historie laat vallen in plaats van erna — dan pakt
    # .iloc[[-1]] de verkeerde (laatste-op-datum) rij en faalt de featurerij
    # met HorizonBuitenBereik. Geen realistisch scenario, dus hier gefixt.
    historie = pd.DataFrame({
        "Store": 1, "Date": pd.date_range("2015-06-01", periods=30, freq="D"),
        "Sales": np.random.default_rng(2).uniform(500, 2000, 30), "Open": 1,
    })
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    return artifact.schrijf_artefact(
        basis_map=tmp_path / "models", modellen=modellen, historie=historie,
        winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.15, "coverage_p10_p90": 0.79, "n_observaties": 500},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=30, versleuteld=False,
    )


def _inloggen(client):
    resp = client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "een-goed-wachtwoord"})
    assert resp.status_code == 200, resp.text


def test_voorbeeld_forecast_werkt_zonder_eigen_winkelbinding(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client)

    resp = client.get("/voorbeeld/forecast")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["store_id"] == 1
    assert len(data["voorspellingen"]) == 14


def test_voorbeeld_forecast_zonder_sessie_geeft_401(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.get("/voorbeeld/forecast")

    assert resp.status_code == 401


def test_voorbeeld_forecast_zonder_configuratie_geeft_503(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch, voorbeeld_store_id=None)
    _inloggen(client)

    resp = client.get("/voorbeeld/forecast")

    assert resp.status_code == 503


def test_voorbeeld_forecast_onbekend_store_id_geeft_503(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch, voorbeeld_store_id="999")
    _inloggen(client)

    resp = client.get("/voorbeeld/forecast")

    assert resp.status_code == 503
