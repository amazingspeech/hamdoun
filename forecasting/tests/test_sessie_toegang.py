"""Sessie-gebaseerde toegang tot /forecast, /metrics en /winkels — het
dashboard gebruikt sinds deze stap de sessiecookie van de ingelogde
gebruiker, geen hardcoded API-key meer. API-key-toegang (voor externe
integraties, bv. een kassasysteem) blijft daarnaast gewoon werken; beide
paden moeten naar dezelfde organisatie-isolatie resolven."""
import importlib
import sys

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from db.api_keys import migreer_bestaande_key
from db.bootstrap import bootstrap_organisatie
from db.gebruiker_winkels import stel_toewijzingen_in
from db.gebruikers import maak_gebruiker
from db.schema import maak_database
from security.api_keys import hash_key
from training import artifact, train


def _bouw_omgeving(tmp_path, monkeypatch, store_ids=(1,)):
    modellen = train.train_alle_kwantielen(pd.DataFrame({
        **{k: np.random.default_rng(1).uniform(0, 100, 200) for k in train.FEATURE_KOLOMMEN},
        "Sales": np.random.default_rng(1).uniform(500, 2000, 200),
        "Open": 1,
    }))
    historie = pd.concat([
        pd.DataFrame({
            "Store": store, "Date": pd.date_range("2015-06-01", periods=40, freq="D"),
            "Sales": np.random.default_rng(2 + store).uniform(500, 2000, 40), "Open": 1,
        })
        for store in store_ids
    ], ignore_index=True)
    winkel_metadata = pd.DataFrame({"Store": list(store_ids), "CompetitionDistance": [500.0] * len(store_ids)})
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
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=list(store_ids))
    hash_hex, salt_hex = hash_key("kassasysteem-key")
    migreer_bestaande_key(engine, organisatie_id=org_id, naam="kassasysteem", hash=hash_hex, salt=salt_hex)
    maak_gebruiker(
        engine, organisatie_id=org_id, email="eigenaar@klant.nl", wachtwoord="wachtwoord-123", rol="eigenaar"
    )

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


def test_forecast_werkt_met_geldige_sessie_zonder_api_key(tmp_path, monkeypatch):
    client, _, _ = _bouw_omgeving(tmp_path, monkeypatch)
    client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "wachtwoord-123"})

    resp = client.post("/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3})

    assert resp.status_code == 200


def test_metrics_werkt_met_geldige_sessie_zonder_api_key(tmp_path, monkeypatch):
    client, _, _ = _bouw_omgeving(tmp_path, monkeypatch)
    client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "wachtwoord-123"})

    resp = client.get("/metrics")

    assert resp.status_code == 200


def test_forecast_werkt_nog_steeds_met_api_key_zonder_sessie(tmp_path, monkeypatch):
    client, _, _ = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "kassasysteem-key"},
    )

    assert resp.status_code == 200


def test_forecast_zonder_sessie_en_zonder_api_key_geeft_401(tmp_path, monkeypatch):
    client, _, _ = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.post("/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3})

    assert resp.status_code == 401


def test_winkels_lijst_via_sessie(tmp_path, monkeypatch):
    client, _, _ = _bouw_omgeving(tmp_path, monkeypatch)
    client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "wachtwoord-123"})

    resp = client.get("/winkels")

    assert resp.status_code == 200
    assert resp.json() == [{"extern_store_id": 1, "naam": None}]


def test_winkels_lijst_via_api_key(tmp_path, monkeypatch):
    client, _, _ = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.get("/winkels", headers={"X-API-Key": "kassasysteem-key"})

    assert resp.status_code == 200
    assert resp.json() == [{"extern_store_id": 1, "naam": None}]


def test_winkels_zonder_toegang_geeft_401(tmp_path, monkeypatch):
    client, _, _ = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.get("/winkels")

    assert resp.status_code == 401


def test_lid_ziet_alleen_toegewezen_winkels(tmp_path, monkeypatch):
    client, engine, org_id = _bouw_omgeving(tmp_path, monkeypatch, store_ids=(1, 2))
    lid_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@klant.nl", wachtwoord="wachtwoord-lid")
    stel_toewijzingen_in(engine, gebruiker_id=lid_id, extern_store_ids=[1])
    client.post("/login", json={"email": "lid@klant.nl", "wachtwoord": "wachtwoord-lid"})

    resp = client.get("/winkels")

    assert resp.status_code == 200
    assert [w["extern_store_id"] for w in resp.json()] == [1]


def test_eigenaar_ziet_alle_winkels_ondanks_ontbrekende_toewijzing(tmp_path, monkeypatch):
    """Toewijzing is puur een lid-concept — een eigenaar heeft altijd
    org-brede toegang, ook al bestaat er geen gebruiker_winkels-rij voor
    ze."""
    client, _, _ = _bouw_omgeving(tmp_path, monkeypatch, store_ids=(1, 2))
    client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "wachtwoord-123"})

    resp = client.get("/winkels")

    assert resp.status_code == 200
    assert {w["extern_store_id"] for w in resp.json()} == {1, 2}


def test_forecast_voor_toegewezen_winkel_werkt_voor_lid(tmp_path, monkeypatch):
    client, engine, org_id = _bouw_omgeving(tmp_path, monkeypatch, store_ids=(1, 2))
    lid_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@klant.nl", wachtwoord="wachtwoord-lid")
    stel_toewijzingen_in(engine, gebruiker_id=lid_id, extern_store_ids=[1])
    client.post("/login", json={"email": "lid@klant.nl", "wachtwoord": "wachtwoord-lid"})

    resp = client.post("/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3})

    assert resp.status_code == 200


def test_forecast_voor_niet_toegewezen_winkel_geeft_404_voor_lid(tmp_path, monkeypatch):
    """De winkel bestaat wél binnen de organisatie (geen cross-tenant-geval)
    maar is niet aan dit lid toegewezen — zelfde 404-i.p.v.-403-redenering
    als de bestaande tenant-isolatie: bevestig nooit dat een store_id
    bestaat maar niet van jou is."""
    client, engine, org_id = _bouw_omgeving(tmp_path, monkeypatch, store_ids=(1, 2))
    lid_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@klant.nl", wachtwoord="wachtwoord-lid")
    stel_toewijzingen_in(engine, gebruiker_id=lid_id, extern_store_ids=[1])
    client.post("/login", json={"email": "lid@klant.nl", "wachtwoord": "wachtwoord-lid"})

    resp = client.post("/forecast", json={"store_id": 2, "start_datum": "2015-07-11", "horizon_dagen": 3})

    assert resp.status_code == 404


def test_forecast_via_api_key_negeert_winkeltoewijzing(tmp_path, monkeypatch):
    """API-keys blijven org-breed werken — er is geen gebruiker/rol aan een
    key gekoppeld, dus geen toewijzing om op te handhaven."""
    client, _, _ = _bouw_omgeving(tmp_path, monkeypatch, store_ids=(1, 2))

    resp = client.post(
        "/forecast", json={"store_id": 2, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "kassasysteem-key"},
    )

    assert resp.status_code == 200
