"""Stripe subscription lifecycle: als een organisatie gedeactiveerd is
(POST /webhooks/stripe: customer.subscription.deleted, zie
tests/test_stripe_webhook_endpoint.py), moet dat daadwerkelijk toegang
intrekken — niet alleen een vlag zetten die nergens gelezen wordt. Toetst
alle drie de plekken waar organisatie_id wordt opgelost: login,
vereis_sessie (sessie-pad) en vereis_toegang (zowel API-key- als
sessie-pad)."""
import importlib
import sys

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from db.api_keys import migreer_bestaande_key
from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.organisaties import deactiveer_organisatie
from db.schema import maak_database
from security.api_keys import hash_key
from training import artifact, train


def _bouw_omgeving(tmp_path, monkeypatch):
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
    org_id = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[1])
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@klant.nl", wachtwoord="correct-paard", rol="eigenaar")
    hash_hex, salt_hex = hash_key("een-geldige-api-key")
    migreer_bestaande_key(engine, organisatie_id=org_id, naam="key-a", hash=hash_hex, salt=salt_hex)

    monkeypatch.setenv("MODEL_VERSION", versie)
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tenants_db_pad))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", "1000")
    monkeypatch.setenv("SESSIE_COOKIE_SECURE", "false")

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return TestClient(module.app), engine, org_id


def test_login_wordt_geweigerd_voor_gedeactiveerde_organisatie(tmp_path, monkeypatch):
    client, engine, org_id = _bouw_omgeving(tmp_path, monkeypatch)
    deactiveer_organisatie(engine, organisatie_id=org_id)

    resp = client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "correct-paard"})

    assert resp.status_code == 403


def test_login_werkt_nog_voor_actieve_organisatie(tmp_path, monkeypatch):
    client, engine, org_id = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "correct-paard"})

    assert resp.status_code == 200


def test_bestaande_sessie_wordt_geweigerd_na_deactivatie(tmp_path, monkeypatch):
    client, engine, org_id = _bouw_omgeving(tmp_path, monkeypatch)
    login_resp = client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "correct-paard"})
    assert login_resp.status_code == 200

    deactiveer_organisatie(engine, organisatie_id=org_id)
    resp = client.get("/me")

    assert resp.status_code == 403


def test_forecast_via_api_key_wordt_geweigerd_na_deactivatie(tmp_path, monkeypatch):
    client, engine, org_id = _bouw_omgeving(tmp_path, monkeypatch)
    deactiveer_organisatie(engine, organisatie_id=org_id)

    resp = client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "een-geldige-api-key"},
    )

    assert resp.status_code == 403


def test_forecast_via_api_key_werkt_nog_voor_actieve_organisatie(tmp_path, monkeypatch):
    client, engine, org_id = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "een-geldige-api-key"},
    )

    assert resp.status_code == 200


def test_forecast_via_sessie_wordt_geweigerd_na_deactivatie(tmp_path, monkeypatch):
    client, engine, org_id = _bouw_omgeving(tmp_path, monkeypatch)
    login_resp = client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "correct-paard"})
    assert login_resp.status_code == 200

    deactiveer_organisatie(engine, organisatie_id=org_id)
    resp = client.post("/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3})

    assert resp.status_code == 403
