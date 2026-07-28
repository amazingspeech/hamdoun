"""Fase 4 Stap 4: wachtwoord-reset. security.mail.verstuur wordt
gemonkeypatcht (dat is al apart getest in tests/test_mail.py) — hier
wordt alleen getest wat de endpoints daarmee doen."""
import importlib
import sys

from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker, verifieer_inloggegevens
from db.schema import maak_database
from db.sessies import maak_sessie, vind_gebruiker_voor_sessie
from db.wachtwoord_reset import maak_reset_token


def _bouw_omgeving(tmp_path, monkeypatch):
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")
    (tmp_path / "models").mkdir()

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)
    org_id = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[])
    gebruiker_id = maak_gebruiker(engine, organisatie_id=org_id, email="test@klant.nl", wachtwoord="oud-wachtwoord")

    monkeypatch.setenv("MODEL_VERSION", _bootstrap_model(tmp_path))
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tenants_db_pad))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", "1000")
    monkeypatch.setenv("SESSIE_COOKIE_SECURE", "false")
    monkeypatch.setenv("MAIL_SMTP_HOST", "smtp.test.nl")
    monkeypatch.setenv("MAIL_SMTP_POORT", "587")
    monkeypatch.setenv("MAIL_AFZENDER", "info@test.nl")
    monkeypatch.setenv("MAIL_SMTP_GEBRUIKER", "info@test.nl")
    monkeypatch.setenv("MAIL_SMTP_WACHTWOORD", "geheim")
    monkeypatch.setenv("APP_BASIS_URL", "http://127.0.0.1:8000")

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return module, TestClient(module.app), engine, gebruiker_id


def _bootstrap_model(tmp_path):
    import numpy as np
    import pandas as pd

    from training import artifact, train

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
    return artifact.schrijf_artefact(
        basis_map=tmp_path / "models", modellen=modellen, historie=historie,
        winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.15, "coverage_p10_p90": 0.79, "n_observaties": 500},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=30, versleuteld=False,
    )


def test_aanvragen_met_bestaand_email_verstuurt_mail(tmp_path, monkeypatch):
    module, client, engine, gebruiker_id = _bouw_omgeving(tmp_path, monkeypatch)
    verzonden = []
    monkeypatch.setattr(module.mail, "verstuur", lambda **kwargs: verzonden.append(kwargs))

    resp = client.post("/wachtwoord-reset/aanvragen", json={"email": "test@klant.nl"})

    assert resp.status_code == 200
    assert len(verzonden) == 1
    assert verzonden[0]["ontvanger"] == "test@klant.nl"
    assert "http://127.0.0.1:8000/wachtwoord-resetten.html?token=" in verzonden[0]["tekst"]


def test_aanvragen_met_onbekend_email_geeft_zelfde_generieke_response(tmp_path, monkeypatch):
    module, client, engine, gebruiker_id = _bouw_omgeving(tmp_path, monkeypatch)
    verzonden = []
    monkeypatch.setattr(module.mail, "verstuur", lambda **kwargs: verzonden.append(kwargs))

    resp_bestaand = client.post("/wachtwoord-reset/aanvragen", json={"email": "test@klant.nl"})
    resp_onbekend = client.post("/wachtwoord-reset/aanvragen", json={"email": "bestaat-niet@klant.nl"})

    assert resp_bestaand.status_code == resp_onbekend.status_code == 200
    assert resp_bestaand.json() == resp_onbekend.json()
    assert len(verzonden) == 1  # alleen voor het bestaande e-mailadres echt verstuurd


def test_aanvragen_mislukte_mail_lekt_niets_naar_de_client(tmp_path, monkeypatch):
    module, client, engine, gebruiker_id = _bouw_omgeving(tmp_path, monkeypatch)

    def _faal(**kwargs):
        raise RuntimeError("gesimuleerde SMTP-storing")
    monkeypatch.setattr(module.mail, "verstuur", _faal)

    resp = client.post("/wachtwoord-reset/aanvragen", json={"email": "test@klant.nl"})

    assert resp.status_code == 200


def test_voltooien_met_geldig_token_wijzigt_wachtwoord(tmp_path, monkeypatch):
    module, client, engine, gebruiker_id = _bouw_omgeving(tmp_path, monkeypatch)
    token = maak_reset_token(engine, gebruiker_id=gebruiker_id)

    resp = client.post(
        "/wachtwoord-reset/voltooien", json={"token": token, "nieuw_wachtwoord": "gloednieuw-wachtwoord"}
    )

    assert resp.status_code == 200
    assert verifieer_inloggegevens(engine, email="test@klant.nl", wachtwoord="oud-wachtwoord") is None
    assert verifieer_inloggegevens(engine, email="test@klant.nl", wachtwoord="gloednieuw-wachtwoord") == gebruiker_id


def test_voltooien_trekt_bestaande_sessies_in(tmp_path, monkeypatch):
    module, client, engine, gebruiker_id = _bouw_omgeving(tmp_path, monkeypatch)
    oude_sessie = maak_sessie(engine, gebruiker_id=gebruiker_id)
    token = maak_reset_token(engine, gebruiker_id=gebruiker_id)

    client.post("/wachtwoord-reset/voltooien", json={"token": token, "nieuw_wachtwoord": "gloednieuw-wachtwoord"})

    assert vind_gebruiker_voor_sessie(engine, oude_sessie) is None


def test_voltooien_token_kan_niet_hergebruikt_worden(tmp_path, monkeypatch):
    module, client, engine, gebruiker_id = _bouw_omgeving(tmp_path, monkeypatch)
    token = maak_reset_token(engine, gebruiker_id=gebruiker_id)
    client.post("/wachtwoord-reset/voltooien", json={"token": token, "nieuw_wachtwoord": "eerste-nieuwe"})

    resp = client.post("/wachtwoord-reset/voltooien", json={"token": token, "nieuw_wachtwoord": "tweede-nieuwe"})

    assert resp.status_code == 400


def test_voltooien_met_ongeldig_token_geeft_400(tmp_path, monkeypatch):
    module, client, engine, gebruiker_id = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.post(
        "/wachtwoord-reset/voltooien", json={"token": "bestaat-niet", "nieuw_wachtwoord": "gloednieuw-wachtwoord"}
    )

    assert resp.status_code == 400


def test_voltooien_te_kort_wachtwoord_geeft_422(tmp_path, monkeypatch):
    module, client, engine, gebruiker_id = _bouw_omgeving(tmp_path, monkeypatch)
    token = maak_reset_token(engine, gebruiker_id=gebruiker_id)

    resp = client.post("/wachtwoord-reset/voltooien", json={"token": token, "nieuw_wachtwoord": "kort"})

    assert resp.status_code == 422
