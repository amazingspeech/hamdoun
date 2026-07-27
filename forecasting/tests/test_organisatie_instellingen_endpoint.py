"""Fase 5 NODIG 1: eigenaar-only endpoint om de gemiddelde omzet per stuk
in te stellen, nodig voor het herbestel-advies op /forecast. Aparte fixture
van test_gebruikers_endpoint.py: die test teambeheer zelf, dit bestand
test specifiek de organisatie-instellingen eronder."""
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


def test_zonder_ingestelde_prijs_geeft_none(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.get("/organisatie/instellingen")

    assert resp.status_code == 200
    assert resp.json() == {"gemiddelde_omzet_per_stuk": None}


def test_eigenaar_kan_prijs_instellen_en_teruglezen(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    put_resp = client.put("/organisatie/instellingen", json={"gemiddelde_omzet_per_stuk": 12.5})
    assert put_resp.status_code == 200
    assert put_resp.json() == {"gemiddelde_omzet_per_stuk": 12.5}

    get_resp = client.get("/organisatie/instellingen")
    assert get_resp.json() == {"gemiddelde_omzet_per_stuk": 12.5}


def test_lid_mag_prijs_niet_wijzigen(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.put("/organisatie/instellingen", json={"gemiddelde_omzet_per_stuk": 12.5})

    assert resp.status_code == 403


def test_lid_mag_prijs_wel_lezen(tmp_path, monkeypatch):
    """De prijs zelf is geen geheim — een lid heeft 'm nodig om het
    herbestel-advies op /forecast te kunnen zien, niet om te wijzigen."""
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.get("/organisatie/instellingen")

    assert resp.status_code == 200


def test_prijs_instellen_zonder_sessie_geeft_401(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.put("/organisatie/instellingen", json={"gemiddelde_omzet_per_stuk": 12.5})

    assert resp.status_code == 401


def test_prijs_instellen_met_nul_geeft_422(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.put("/organisatie/instellingen", json={"gemiddelde_omzet_per_stuk": 0})

    assert resp.status_code == 422


def test_prijs_blijft_geisoleerd_tussen_organisaties(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    client.put("/organisatie/instellingen", json={"gemiddelde_omzet_per_stuk": 12.5})

    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")
    resp = client.get("/organisatie/instellingen")

    assert resp.json() == {"gemiddelde_omzet_per_stuk": None}
