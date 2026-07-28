"""Fase 4 Stap 3: login/logout/sessiebeheer via HttpOnly-cookies. Aparte
fixture van test_app.py: die bouwt een organisatie met API-key, dit bestand
bouwt een organisatie met een gebruikersaccount."""
import importlib
import sys

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database
from training import artifact, train


def _bouw_login_omgeving(tmp_path, monkeypatch, rate_limit_per_minuut="1000"):
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

    # api_keys.json blijft nodig omdat serving/config.py 'm nog vereist
    # (bewust nog niet opgeruimd in Stap 2, zie FASE4-SAAS-FOUNDATION.md).
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)
    org_id = bootstrap_organisatie(engine, naam="Test organisatie", slug="test-organisatie", store_ids=[1])
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@klant.nl", wachtwoord="een-goed-wachtwoord")

    monkeypatch.setenv("MODEL_VERSION", versie)
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tenants_db_pad))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", rate_limit_per_minuut)
    monkeypatch.setenv("SESSIE_COOKIE_SECURE", "false")  # TestClient praat geen https

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return TestClient(module.app), engine


def test_login_met_juiste_gegevens_zet_sessiecookie(tmp_path, monkeypatch):
    client, _ = _bouw_login_omgeving(tmp_path, monkeypatch)
    resp = client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "een-goed-wachtwoord"})
    assert resp.status_code == 200
    assert "sessie" in resp.cookies


def test_login_met_fout_wachtwoord_geeft_401_zonder_cookie(tmp_path, monkeypatch):
    client, _ = _bouw_login_omgeving(tmp_path, monkeypatch)
    resp = client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "verkeerd"})
    assert resp.status_code == 401
    assert "sessie" not in resp.cookies


def test_login_met_onbekend_email_geeft_401(tmp_path, monkeypatch):
    client, _ = _bouw_login_omgeving(tmp_path, monkeypatch)
    resp = client.post("/login", json={"email": "onbekend@klant.nl", "wachtwoord": "een-goed-wachtwoord"})
    assert resp.status_code == 401


def test_me_zonder_sessie_geeft_401(tmp_path, monkeypatch):
    client, _ = _bouw_login_omgeving(tmp_path, monkeypatch)
    resp = client.get("/me")
    assert resp.status_code == 401


def test_me_met_geldige_sessie_geeft_gebruiker(tmp_path, monkeypatch):
    client, _ = _bouw_login_omgeving(tmp_path, monkeypatch)
    client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "een-goed-wachtwoord"})

    resp = client.get("/me")

    assert resp.status_code == 200
    assert resp.json()["email"] == "eigenaar@klant.nl"


def test_me_geeft_in_proefperiode_false_voor_handmatig_aangemaakte_org(tmp_path, monkeypatch):
    """bootstrap_organisatie zet nooit trial_verloopt_op — de frontend
    gebruikt dit veld om premium-functies (self-serve API-keys, promotie/
    schoolvakantie-invoer, CSV/PNG-export) zichtbaar-maar-uitgeschakeld te
    tonen tijdens een proefperiode."""
    client, _ = _bouw_login_omgeving(tmp_path, monkeypatch)
    client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "een-goed-wachtwoord"})

    resp = client.get("/me")

    assert resp.json()["in_proefperiode"] is False


def test_me_geeft_in_proefperiode_true_tijdens_proefperiode(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from db.schema import organisaties

    client, engine = _bouw_login_omgeving(tmp_path, monkeypatch)
    with engine.begin() as conn:
        org_id = conn.execute(select(organisaties.c.id).where(organisaties.c.slug == "test-organisatie")).scalar_one()
        conn.execute(
            organisaties.update().where(organisaties.c.id == org_id).values(
                trial_verloopt_op=datetime.now(timezone.utc) + timedelta(days=14)
            )
        )
    client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "een-goed-wachtwoord"})

    resp = client.get("/me")

    assert resp.json()["in_proefperiode"] is True


def test_me_geeft_trial_verloopt_op_mee_tijdens_proefperiode(tmp_path, monkeypatch):
    """De zijbalk toont hoeveel dagen er nog in de proefperiode over zijn
    (zie dashboard/account.js) — daarvoor moet /me de vervaldatum zelf
    meegeven, niet alleen het boolean in_proefperiode."""
    from datetime import date, datetime, timedelta, timezone

    from sqlalchemy import select

    from db.schema import organisaties

    client, engine = _bouw_login_omgeving(tmp_path, monkeypatch)
    verloopt_op = datetime.now(timezone.utc) + timedelta(days=14)
    with engine.begin() as conn:
        org_id = conn.execute(select(organisaties.c.id).where(organisaties.c.slug == "test-organisatie")).scalar_one()
        conn.execute(
            organisaties.update().where(organisaties.c.id == org_id).values(trial_verloopt_op=verloopt_op)
        )
    client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "een-goed-wachtwoord"})

    resp = client.get("/me")

    assert resp.json()["trial_verloopt_op"] == verloopt_op.date().isoformat()


def test_me_geeft_geen_trial_verloopt_op_mee_zonder_proefperiode(tmp_path, monkeypatch):
    client, _ = _bouw_login_omgeving(tmp_path, monkeypatch)
    client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "een-goed-wachtwoord"})

    resp = client.get("/me")

    assert resp.json()["trial_verloopt_op"] is None


def test_logout_maakt_sessie_ongeldig(tmp_path, monkeypatch):
    client, _ = _bouw_login_omgeving(tmp_path, monkeypatch)
    client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "een-goed-wachtwoord"})

    logout_resp = client.post("/logout")
    assert logout_resp.status_code == 200

    resp = client.get("/me")
    assert resp.status_code == 401


def test_login_boven_rate_limit_geeft_429(tmp_path, monkeypatch):
    client, _ = _bouw_login_omgeving(tmp_path, monkeypatch, rate_limit_per_minuut="2")
    verzoek = {"email": "eigenaar@klant.nl", "wachtwoord": "verkeerd"}

    for _ in range(2):
        resp = client.post("/login", json=verzoek)
        assert resp.status_code == 401

    resp = client.post("/login", json=verzoek)
    assert resp.status_code == 429
