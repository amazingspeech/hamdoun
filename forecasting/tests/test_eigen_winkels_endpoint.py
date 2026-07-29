"""Zelfde fixture-vorm als tests/test_api_keys_endpoint.py."""
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
    return TestClient(module.app), engine


def _inloggen(client, email, wachtwoord):
    resp = client.post("/login", json={"email": email, "wachtwoord": wachtwoord})
    assert resp.status_code == 200, resp.text


def test_eigenaar_kan_eigen_winkel_aanmaken(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["naam"] == "Webshop A"
    assert data["heeft_verkoopdata"] is False
    assert data["gemiddelde_omzet_per_stuk"] is None


def test_lid_kan_geen_eigen_winkel_aanmaken(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})

    assert resp.status_code == 403


def test_dubbele_naam_geeft_409(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})

    resp = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})

    assert resp.status_code == 409


def test_lid_kan_eigen_winkels_lijst_lezen(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})
    client.post("/logout")
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.get("/organisatie/eigen-winkels")

    assert resp.status_code == 200
    assert [w["naam"] for w in resp.json()] == ["Webshop A"]


def test_eigen_winkels_lijst_toont_alleen_eigen_organisatie(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.get("/organisatie/eigen-winkels")

    assert resp.json() == []


def test_hernoemen_werkt(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]

    resp = client.patch(f"/organisatie/eigen-winkels/{winkel_id}", json={"naam": "Webshop B"})

    assert resp.status_code == 200
    assert resp.json()["naam"] == "Webshop B"


def test_hernoemen_andermans_winkel_geeft_404(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.patch(f"/organisatie/eigen-winkels/{winkel_id}", json={"naam": "Overname"})

    assert resp.status_code == 404


def test_verwijderen_werkt(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]

    resp = client.delete(f"/organisatie/eigen-winkels/{winkel_id}")

    assert resp.status_code == 204
    assert client.get("/organisatie/eigen-winkels").json() == []


def test_verwijderen_andermans_winkel_geeft_404(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.delete(f"/organisatie/eigen-winkels/{winkel_id}")

    assert resp.status_code == 404


def test_prijs_instellen_werkt(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]

    resp = client.put(f"/organisatie/eigen-winkels/{winkel_id}/instellingen", json={"gemiddelde_omzet_per_stuk": 24.5})

    assert resp.status_code == 200
    assert resp.json()["gemiddelde_omzet_per_stuk"] == 24.5


def test_prijs_instellen_andermans_winkel_geeft_404(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.put(f"/organisatie/eigen-winkels/{winkel_id}/instellingen", json={"gemiddelde_omzet_per_stuk": 24.5})

    assert resp.status_code == 404
