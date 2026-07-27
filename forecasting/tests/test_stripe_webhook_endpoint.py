"""Fase 5 NODIG 5: POST /webhooks/stripe rondt een self-serve aanmelding af
zodra Stripe checkout.session.completed meldt. De Stripe-signature-
verificatie zelf wordt gemonkeypatcht (serving.app.lees_webhook_event) —
dat is precies de functie die al apart getest is in
tests/test_betaalintegratie.py; hier wordt alleen getest wat er ná een
geverifieerd event gebeurt."""
import importlib
import sys

from fastapi.testclient import TestClient

from db.aanmeldingen import haal_aanmelding_bij_sessie, maak_aanmelding
from db.gebruikers import verifieer_inloggegevens
from db.schema import maak_database
from security.api_keys import hash_key


def _bouw_omgeving(tmp_path, monkeypatch):
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
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_geheim")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_geheim")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_abc")
    monkeypatch.setenv("APP_BASIS_URL", "http://127.0.0.1:8000")

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return module, TestClient(module.app, raise_server_exceptions=False), engine


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


class _NepStripeObject:
    """De echte Stripe SDK geeft nooit een plain dict terug voor een
    event-object — StripeObject ondersteunt itemtoegang ([]) maar GEEN
    .get() (zie stripe._stripe_object.StripeObject: .get() bestaat niet,
    __getattr__ probeert het als veldnaam te lezen en faalt dan met een
    AttributeError). Een plain dict als test-double zou deze fout gemist
    hebben, want die ondersteunt .get() wél — vandaar deze eigen klasse."""

    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]


def _checkout_completed_event(sessie_id, customer_id="cus_123", subscription_id="sub_456"):
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": _NepStripeObject({"id": sessie_id, "customer": customer_id, "subscription": subscription_id})
        },
    }


def _subscription_deleted_event(subscription_id):
    return {
        "type": "customer.subscription.deleted",
        "data": {"object": _NepStripeObject({"id": subscription_id})},
    }


def _leg_aanmelding_vast(engine, sessie_id="cs_test_123"):
    hash_hex, salt_hex = hash_key("correct-paard")
    return maak_aanmelding(
        engine, organisatie_naam="Bakkerij De Vries", organisatie_slug="bakkerij-de-vries",
        email="devries@voorbeeld.nl", wachtwoord_hash=hash_hex, wachtwoord_salt=salt_hex,
        stripe_checkout_session_id=sessie_id,
    )


def test_checkout_completed_maakt_organisatie_en_eigenaar_aan(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _leg_aanmelding_vast(engine)
    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _checkout_completed_event("cs_test_123"))

    resp = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})

    assert resp.status_code == 200, resp.text
    gebruiker_id = verifieer_inloggegevens(engine, email="devries@voorbeeld.nl", wachtwoord="correct-paard")
    assert gebruiker_id is not None

    aanmelding = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    assert aanmelding.organisatie_id is not None
    assert aanmelding.voltooid_op is not None

    from sqlalchemy import select

    from db.schema import organisaties
    with engine.connect() as conn:
        org = conn.execute(select(organisaties).where(organisaties.c.id == aanmelding.organisatie_id)).one()
    assert org.naam == "Bakkerij De Vries"
    assert org.slug == "bakkerij-de-vries"
    assert org.stripe_customer_id == "cus_123"
    assert org.stripe_subscription_id == "sub_456"


def test_checkout_completed_zet_trial_verloopt_op(tmp_path, monkeypatch):
    """De lokale proefperiode-status (db.organisaties.is_in_proefperiode)
    moet Stripe's eigen trial_period_days volgen (SIGNUP_PROEFPERIODE_DAGEN,
    zie serving/app.py) — anders weet de app niet welke organisaties nog
    premium-functies moeten missen."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from db.schema import organisaties

    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _leg_aanmelding_vast(engine)
    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _checkout_completed_event("cs_test_123"))
    voor = datetime.now(timezone.utc)

    resp = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})
    na = datetime.now(timezone.utc)

    assert resp.status_code == 200, resp.text
    aanmelding = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    with engine.connect() as conn:
        org = conn.execute(select(organisaties).where(organisaties.c.id == aanmelding.organisatie_id)).one()
    verwachte_ondergrens = (voor + timedelta(days=module.SIGNUP_PROEFPERIODE_DAGEN)).replace(tzinfo=None)
    verwachte_bovengrens = (na + timedelta(days=module.SIGNUP_PROEFPERIODE_DAGEN)).replace(tzinfo=None)
    assert verwachte_ondergrens <= org.trial_verloopt_op <= verwachte_bovengrens


def test_nieuwe_eigenaar_kan_meteen_inloggen(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _leg_aanmelding_vast(engine)
    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _checkout_completed_event("cs_test_123"))
    client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})

    resp = client.post("/login", json={"email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard"})

    assert resp.status_code == 200


def test_subscription_deleted_deactiveert_de_organisatie(tmp_path, monkeypatch):
    from db.organisaties import is_actief

    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _leg_aanmelding_vast(engine)
    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _checkout_completed_event("cs_test_123"))
    client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})
    aanmelding = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    assert is_actief(engine, organisatie_id=aanmelding.organisatie_id) is True

    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _subscription_deleted_event("sub_456"))
    resp = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})

    assert resp.status_code == 200, resp.text
    assert is_actief(engine, organisatie_id=aanmelding.organisatie_id) is False


def test_subscription_deleted_onbekende_subscription_wordt_genegeerd(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _subscription_deleted_event("sub_onbekend"))

    resp = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})

    assert resp.status_code == 200


def test_dubbel_event_maakt_niet_een_tweede_organisatie_aan(tmp_path, monkeypatch):
    """Stripe kan hetzelfde event meermaals afleveren (at-least-once
    delivery) — een tweede aflevering mag geen tweede organisatie of
    gebruiker aanmaken."""
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _leg_aanmelding_vast(engine)
    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _checkout_completed_event("cs_test_123"))
    eerste = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})
    assert eerste.status_code == 200

    tweede = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})

    assert tweede.status_code == 200
    from sqlalchemy import select

    from db.schema import gebruikers
    with engine.connect() as conn:
        aantal = len(conn.execute(select(gebruikers).where(gebruikers.c.email == "devries@voorbeeld.nl")).all())
    assert aantal == 1


def test_gedeeltelijke_fout_tijdens_verwerking_kan_veilig_herhaald_worden(tmp_path, monkeypatch):
    """Stripe herhaalt een webhook-aflevering automatisch als het endpoint
    geen 2xx teruggeeft. Als de verwerking halverwege faalt (bv. een
    tijdelijke DB-fout nadat de organisatie al is aangemaakt maar vóórdat
    de aanmelding als voltooid is gemarkeerd), moet die automatische retry
    alsnog veilig slagen — niet stuklopen op een dubbele organisatie/
    gebruiker doordat de eerste, mislukte poging al gedeeltelijke rijen
    achterliet."""
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _leg_aanmelding_vast(engine)
    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _checkout_completed_event("cs_test_123"))

    origineel = module.db_organisaties.stel_stripe_koppeling_in
    aanroepen = {"aantal": 0}

    def _faal_eerste_keer(*args, **kwargs):
        aanroepen["aantal"] += 1
        if aanroepen["aantal"] == 1:
            raise RuntimeError("gesimuleerde tijdelijke fout")
        return origineel(*args, **kwargs)

    monkeypatch.setattr(module.db_organisaties, "stel_stripe_koppeling_in", _faal_eerste_keer)

    eerste = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})
    assert eerste.status_code == 500

    tweede = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})
    assert tweede.status_code == 200, tweede.text

    from sqlalchemy import select

    from db.schema import gebruikers, organisaties
    with engine.connect() as conn:
        orgs = conn.execute(select(organisaties).where(organisaties.c.slug == "bakkerij-de-vries")).all()
        gebrs = conn.execute(select(gebruikers).where(gebruikers.c.email == "devries@voorbeeld.nl")).all()
    assert len(orgs) == 1
    assert len(gebrs) == 1


def test_event_zonder_bekende_aanmelding_wordt_genegeerd(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _checkout_completed_event("cs_onbekend"))

    resp = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})

    assert resp.status_code == 200


def test_ongeldige_signature_geeft_400(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)

    def _faal(**kwargs):
        raise module.OngeldigeWebhookSignature("ongeldig")

    monkeypatch.setattr(module, "lees_webhook_event", _faal)

    resp = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=fout"})

    assert resp.status_code == 400


def test_ander_event_type_wordt_genegeerd(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    monkeypatch.setattr(
        module, "lees_webhook_event", lambda **kw: {"type": "invoice.paid", "data": {"object": {}}}
    )

    resp = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})

    assert resp.status_code == 200
