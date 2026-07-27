"""Fase 4 Stap 7: rate limiting per organisatie i.p.v. per API-key — twee
keys van dezelfde klant mogen niet elk een eigen budget krijgen, anders
verdubbelt (of erger) de effectieve limiet naarmate een organisatie meer
keys aanmaakt. Aparte fixture van test_app.py: die test één key, dit
bestand test expliciet twee keys van dezelfde organisatie."""
import importlib
import sys

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from db.api_keys import migreer_bestaande_key
from db.bootstrap import bootstrap_organisatie
from db.schema import maak_database
from security.api_keys import hash_key
from training import artifact, train


def _bouw_omgeving(tmp_path, monkeypatch, rate_limit_per_minuut):
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
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[1])
    hash_1, salt_1 = hash_key("key-een")
    hash_2, salt_2 = hash_key("key-twee")
    migreer_bestaande_key(engine, organisatie_id=org_id, naam="key-een", hash=hash_1, salt=salt_1)
    migreer_bestaande_key(engine, organisatie_id=org_id, naam="key-twee", hash=hash_2, salt=salt_2)

    monkeypatch.setenv("MODEL_VERSION", versie)
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tenants_db_pad))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", rate_limit_per_minuut)

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return TestClient(module.app)


def test_rate_limit_wordt_gedeeld_tussen_keys_van_dezelfde_organisatie(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch, rate_limit_per_minuut="2")
    verzoek = {"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3}

    resp1 = client.post("/forecast", json=verzoek, headers={"X-API-Key": "key-een"})
    resp2 = client.post("/forecast", json=verzoek, headers={"X-API-Key": "key-twee"})
    assert resp1.status_code == 200
    assert resp2.status_code == 200

    # Beide voorgaande aanvragen kwamen van dezelfde organisatie (twee
    # verschillende keys) — de gedeelde limiet van 2 is nu op, ongeacht
    # welke van de twee keys de derde aanvraag doet.
    resp3 = client.post("/forecast", json=verzoek, headers={"X-API-Key": "key-een"})
    assert resp3.status_code == 429
