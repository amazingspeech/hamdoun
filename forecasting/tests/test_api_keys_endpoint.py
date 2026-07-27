"""Fase 4 Stap 6: zelfbediening van API-keys. Zelfde fixture-vorm als
tests/test_gebruikers_endpoint.py — een eigenaar en een lid in
organisatie A, een aparte organisatie B om isolatie te toetsen."""
import importlib
import sys

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database
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
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Organisatie B", slug="org-b", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_a, email="eigenaar-a@klant.nl", wachtwoord="wachtwoord-a", rol="eigenaar")
    maak_gebruiker(engine, organisatie_id=org_a, email="lid-a@klant.nl", wachtwoord="wachtwoord-a-lid", rol="lid")
    maak_gebruiker(engine, organisatie_id=org_b, email="eigenaar-b@klant.nl", wachtwoord="wachtwoord-b", rol="eigenaar")

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
    return TestClient(module.app)


def _inloggen(client, email, wachtwoord):
    resp = client.post("/login", json={"email": email, "wachtwoord": wachtwoord})
    assert resp.status_code == 200, resp.text


def test_eigenaar_kan_api_key_aanmaken(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.post("/api-keys", json={"naam": "Kassasysteem"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["naam"] == "Kassasysteem"
    assert data["ruwe_key"].startswith("vk_")


def test_nieuwe_api_key_werkt_voor_forecast_auth(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    ruwe_key = client.post("/api-keys", json={"naam": "Kassasysteem"}).json()["ruwe_key"]

    resp = client.get("/metrics", headers={"X-API-Key": ruwe_key})

    assert resp.status_code == 200


def test_lid_mag_geen_api_key_aanmaken(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.post("/api-keys", json={"naam": "Kassasysteem"})

    assert resp.status_code == 403


def test_api_key_aanmaken_zonder_sessie_geeft_401(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.post("/api-keys", json={"naam": "Kassasysteem"})

    assert resp.status_code == 401


def test_api_keys_lijst_toont_alleen_eigen_organisatie_zonder_ruwe_waarde(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    client.post("/api-keys", json={"naam": "Kassasysteem"})

    resp = client.get("/api-keys")

    assert resp.status_code == 200
    data = resp.json()
    assert {rij["naam"] for rij in data} == {"Kassasysteem"}
    assert "ruwe_key" not in data[0]
    assert "hash" not in data[0]


def test_lid_mag_api_keys_niet_bekijken(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.get("/api-keys")

    assert resp.status_code == 403


def test_eigenaar_kan_eigen_api_key_intrekken(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    key_id = client.post("/api-keys", json={"naam": "Kassasysteem"}).json()["id"]

    resp = client.delete(f"/api-keys/{key_id}")

    assert resp.status_code == 204
    lijst = client.get("/api-keys").json()
    assert lijst[0]["actief"] is False


def test_intrekken_van_andermans_key_geeft_404(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    key_id = client.post("/api-keys", json={"naam": "Kassasysteem"}).json()["id"]
    client.post("/logout")

    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")
    resp = client.delete(f"/api-keys/{key_id}")

    assert resp.status_code == 404
