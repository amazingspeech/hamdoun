import importlib
import sys

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from security import api_keys
from training import artifact, train


def _bouw_test_omgeving(tmp_path, monkeypatch, cors_origins="", rate_limit_per_minuut="1000"):
    modellen = train.train_alle_kwantielen(pd.DataFrame({
        **{k: np.random.default_rng(1).uniform(0, 100, 200) for k in train.FEATURE_KOLOMMEN},
        "Sales": np.random.default_rng(1).uniform(500, 2000, 200),
        "Open": 1,
    }))
    historie = pd.DataFrame({
        "Store": 1, "Date": pd.date_range("2015-06-01", periods=40, freq="D"),
        "Sales": np.random.default_rng(2).uniform(500, 2000, 40), "Open": 1,
    })
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    versie = artifact.schrijf_artefact(
        basis_map=tmp_path / "models", modellen=modellen, historie=historie,
        winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.15, "coverage_p10_p90": 0.79, "n_observaties": 500},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=30, versleuteld=False,
    )

    keys_pad = tmp_path / "api_keys.json"
    api_keys.voeg_key_toe(keys_pad, "test-klant", "test-key-123")

    monkeypatch.setenv("MODEL_VERSION", versie)
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(keys_pad))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", cors_origins)
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", rate_limit_per_minuut)

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return TestClient(module.app)


def test_health_werkt_zonder_auth(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_forecast_zonder_key_geeft_401(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.post("/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3})
    assert resp.status_code == 401


def test_forecast_met_ongeldige_key_geeft_401(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "fout"},
    )
    assert resp.status_code == 401


def test_forecast_met_geldige_key_geeft_voorspellingen(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "test-key-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["voorspellingen"]) == 3
    for dag in data["voorspellingen"]:
        assert dag["p10"] <= dag["p50"] <= dag["p90"]


def test_forecast_onbekende_winkel_geeft_404(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.post(
        "/forecast", json={"store_id": 999, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "test-key-123"},
    )
    assert resp.status_code == 404


def test_forecast_horizon_boven_gevalideerde_periode_geeft_422(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 9999},
        headers={"X-API-Key": "test-key-123"},
    )
    assert resp.status_code == 422


def test_metrics_geeft_gevalideerde_cijfers(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.get("/metrics", headers={"X-API-Key": "test-key-123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["rmspe"] == 0.15
    assert data["coverage_p10_p90"] == 0.79
    assert data["trainingsperiode_eind"] == "2015-06-30"


def test_cors_ontbrekende_config_staat_geen_enkele_origin_toe(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch, cors_origins="")
    resp = client.get(
        "/health", headers={"Origin": "https://willekeurige-site.example"},
    )
    assert "access-control-allow-origin" not in resp.headers


def test_cors_toegestane_origin_krijgt_header(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch, cors_origins="https://tessar.nl")
    resp = client.get("/health", headers={"Origin": "https://tessar.nl"})
    assert resp.headers.get("access-control-allow-origin") == "https://tessar.nl"


def test_audit_log_bevat_verzoek_metadata(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 2},
        headers={"X-API-Key": "test-key-123"},
    )
    import json
    regel = json.loads((tmp_path / "audit.log").read_text(encoding="utf-8").strip().splitlines()[0])
    assert regel["key"] == "test-klant"
    assert regel["statuscode"] == 200
    assert "store_id" in regel


def test_docs_niet_bereikbaar_zonder_expliciete_opt_in(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_docs_bereikbaar_met_expliciete_opt_in(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPOSE_API_DOCS", "true")
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_forecast_boven_rate_limit_geeft_429(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch, rate_limit_per_minuut="2")
    verzoek = {"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3}
    headers = {"X-API-Key": "test-key-123"}

    for _ in range(2):
        resp = client.post("/forecast", json=verzoek, headers=headers)
        assert resp.status_code == 200

    resp = client.post("/forecast", json=verzoek, headers=headers)
    assert resp.status_code == 429
