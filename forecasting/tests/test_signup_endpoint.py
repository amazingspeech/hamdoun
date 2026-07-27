"""Fase 5 NODIG 5: publieke, self-serve /signup — start een Stripe Checkout
Session en legt een 'aanmelding' vast; de echte organisatie + eigenaar-
account ontstaan pas via de webhook zodra de betaling bevestigd is (zie
tests/test_stripe_webhook_endpoint.py). Stripe zelf wordt hier nooit echt
aangeroepen — serving.app.maak_checkout_sessie wordt gemonkeypatcht, zelfde
patroon als de bestaande mail-tests."""
import importlib
import sys

from fastapi.testclient import TestClient

from db.gebruikers import maak_gebruiker
from db.schema import maak_database
from security.api_keys import verifieer_key
from serving.betaalintegratie import CheckoutSessie


def _bouw_omgeving(tmp_path, monkeypatch, met_stripe_config=True):
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")
    (tmp_path / "models").mkdir()

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)

    monkeypatch.setenv("MODEL_VERSION", _bootstrap_model(tmp_path))
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tenants_db_pad))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", "1000")
    monkeypatch.setenv("SESSIE_COOKIE_SECURE", "false")
    if met_stripe_config:
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_geheim")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_geheim")
        monkeypatch.setenv("STRIPE_PRICE_ID", "price_abc")
        monkeypatch.setenv("APP_BASIS_URL", "http://127.0.0.1:8000")
    else:
        for var in ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_ID", "APP_BASIS_URL"):
            monkeypatch.delenv(var, raising=False)

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return module, TestClient(module.app), engine


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


def _fake_checkout_sessie(module, monkeypatch, sessie_id="cs_test_123"):
    aangeroepen_met = {}

    def _nep(**kwargs):
        aangeroepen_met.update(kwargs)
        return CheckoutSessie(id=sessie_id, checkout_url=f"https://checkout.stripe.com/c/pay/{sessie_id}")

    monkeypatch.setattr(module, "maak_checkout_sessie", _nep)
    return aangeroepen_met


def test_signup_geeft_checkout_url_terug(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    aangeroepen_met = _fake_checkout_sessie(module, monkeypatch)

    resp = client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
    })

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"checkout_url": "https://checkout.stripe.com/c/pay/cs_test_123"}
    assert aangeroepen_met["klant_email"] == "devries@voorbeeld.nl"
    assert aangeroepen_met["price_id"] == "price_abc"
    assert aangeroepen_met["proefperiode_dagen"] == 7
    assert aangeroepen_met["success_url"] == "http://127.0.0.1:8000/signup-gelukt.html"
    assert aangeroepen_met["cancel_url"] == "http://127.0.0.1:8000/signup.html"


def test_signup_legt_aanmelding_vast_met_gehasht_wachtwoord(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _fake_checkout_sessie(module, monkeypatch)

    client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
    })

    from db.aanmeldingen import haal_aanmelding_bij_sessie
    rij = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    assert rij is not None
    assert rij.organisatie_naam == "Bakkerij De Vries"
    assert rij.organisatie_slug == "bakkerij-de-vries"
    assert rij.email == "devries@voorbeeld.nl"
    assert rij.wachtwoord_hash != "correct-paard"
    assert verifieer_key("correct-paard", rij.wachtwoord_hash, rij.wachtwoord_salt) is True
    assert rij.organisatie_id is None


def test_signup_met_al_bestaand_email_geeft_409(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _fake_checkout_sessie(module, monkeypatch)
    from db.bootstrap import bootstrap_organisatie
    org_id = bootstrap_organisatie(engine, naam="Bestaande Klant", slug="bestaande-klant", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="devries@voorbeeld.nl", wachtwoord="x")

    resp = client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
    })

    assert resp.status_code == 409


def test_signup_zonder_stripeconfig_geeft_503(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch, met_stripe_config=False)
    # monkeypatch.delenv (in _bouw_omgeving) maakt de Stripe-omgevingsvariabelen
    # onbekend in dit proces, maar serving.app.load_dotenv() zou ze bij een
    # verse module-import alsnog uit een eventueel lokaal .env-bestand kunnen
    # lezen (bv. tijdens live-verificatie, waar dat bestand wél echte Stripe-
    # keys bevat) — deze test moet ongeacht dat lokale bestand blijven kloppen,
    # dus settings hier expliciet overschrijven i.p.v. vertrouwen op de omgeving.
    import dataclasses
    module.settings = dataclasses.replace(
        module.settings, stripe_secret_key=None, stripe_price_id=None, app_basis_url=None
    )

    resp = client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
    })

    assert resp.status_code == 503


def test_signup_te_kort_wachtwoord_geeft_422(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _fake_checkout_sessie(module, monkeypatch)

    resp = client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "kort",
    })

    assert resp.status_code == 422
