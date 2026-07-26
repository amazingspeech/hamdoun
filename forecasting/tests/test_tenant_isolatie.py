"""Fase 4 Stap 2: het letterlijke scenario uit FASE4-SAAS-FOUNDATION.md —
organisatie A met winkel 1 + eigen key, organisatie B met winkel 2 + eigen
key, kruislings alle vier combinaties toetsen. Aparte fixture van
test_app.py: die test één klant, dit bestand test expliciet dat twee
klanten elkaars data nooit kunnen zien."""
import importlib
import json
import sys

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from db.api_keys import migreer_bestaande_key
from db.bootstrap import bootstrap_organisatie
from db.schema import maak_database
from security.api_keys import hash_key
from training import artifact, train


def _bouw_multi_tenant_omgeving(tmp_path, monkeypatch):
    modellen = train.train_alle_kwantielen(pd.DataFrame({
        **{k: np.random.default_rng(1).uniform(0, 100, 200) for k in train.FEATURE_KOLOMMEN},
        "Sales": np.random.default_rng(1).uniform(500, 2000, 200),
        "Open": 1,
    }))
    # Elke winkel krijgt zijn eigen aaneengesloten dagreeks — lag-/
    # rolling-features hebben per winkel consecutieve dagen nodig, dus
    # winkels mogen nooit tegen eenzelfde platte datumreeks verweven worden.
    historie = pd.concat([
        pd.DataFrame({
            "Store": store, "Date": pd.date_range("2015-06-01", periods=40, freq="D"),
            "Sales": np.random.default_rng(store).uniform(500, 2000, 40), "Open": 1,
        })
        for store in (1, 2)
    ], ignore_index=True)
    winkel_metadata = pd.DataFrame({"Store": [1, 2], "CompetitionDistance": [500.0, 750.0]})
    versie = artifact.schrijf_artefact(
        basis_map=tmp_path / "models", modellen=modellen, historie=historie,
        winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.15, "coverage_p10_p90": 0.79, "n_observaties": 500},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=30, versleuteld=False,
    )

    # api_keys.json is nog steeds vereist door serving/config.py (zie
    # FASE4-SAAS-FOUNDATION.md — bewust nog niet opgeruimd in Stap 2), maar
    # de daadwerkelijke auth loopt via de database hieronder.
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[1])
    org_b = bootstrap_organisatie(engine, naam="Organisatie B", slug="org-b", store_ids=[2])
    hash_a, salt_a = hash_key("key-organisatie-a")
    hash_b, salt_b = hash_key("key-organisatie-b")
    migreer_bestaande_key(engine, organisatie_id=org_a, naam="key-a", hash=hash_a, salt=salt_a)
    migreer_bestaande_key(engine, organisatie_id=org_b, naam="key-b", hash=hash_b, salt=salt_b)

    monkeypatch.setenv("MODEL_VERSION", versie)
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tenants_db_pad))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", "1000")

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return TestClient(module.app), tmp_path


@pytest.mark.parametrize("key,store_id,verwacht", [
    ("key-organisatie-a", 1, 200),  # eigen winkel: mag
    ("key-organisatie-b", 2, 200),  # eigen winkel: mag
    ("key-organisatie-a", 2, 404),  # andermans winkel: nooit
    ("key-organisatie-b", 1, 404),  # andermans winkel: nooit
])
def test_organisatie_kan_alleen_eigen_winkel_opvragen(tmp_path, monkeypatch, key, store_id, verwacht):
    client, _ = _bouw_multi_tenant_omgeving(tmp_path, monkeypatch)
    resp = client.post(
        "/forecast", json={"store_id": store_id, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": key},
    )
    assert resp.status_code == verwacht


def test_geweigerde_cross_tenant_poging_komt_in_audit_log_met_organisatie_id(tmp_path, monkeypatch):
    client, werkmap = _bouw_multi_tenant_omgeving(tmp_path, monkeypatch)

    resp = client.post(
        "/forecast", json={"store_id": 2, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "key-organisatie-a"},
    )
    assert resp.status_code == 404

    regel = json.loads((werkmap / "audit.log").read_text(encoding="utf-8").strip().splitlines()[0])
    assert regel["statuscode"] == 404
    assert regel["store_id"] == 2
    assert "organisatie_id" in regel
