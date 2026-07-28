import pytest
import stripe

from serving import betaalintegratie


class _NepSessie:
    def __init__(self, id, url):
        self.id = id
        self.url = url


def test_maak_checkout_sessie_geeft_id_en_url_terug(monkeypatch):
    aangeroepen_met = {}

    def _nep_create(**kwargs):
        aangeroepen_met.update(kwargs)
        return _NepSessie(id="cs_test_123", url="https://checkout.stripe.com/c/pay/cs_test_123")

    monkeypatch.setattr(betaalintegratie.stripe.checkout.Session, "create", _nep_create)

    resultaat = betaalintegratie.maak_checkout_sessie(
        stripe_secret_key="sk_test_geheim",
        price_id="price_abc",
        klant_email="devries@voorbeeld.nl",
        success_url="https://app.voorbeeld.nl/signup-gelukt.html",
        cancel_url="https://app.voorbeeld.nl/signup.html",
        metadata={"aanmelding_id": "42"},
        proefperiode_dagen=7,
    )

    assert resultaat.id == "cs_test_123"
    assert resultaat.checkout_url == "https://checkout.stripe.com/c/pay/cs_test_123"
    assert aangeroepen_met["api_key"] == "sk_test_geheim"
    assert aangeroepen_met["mode"] == "subscription"
    assert aangeroepen_met["line_items"] == [{"price": "price_abc", "quantity": 1}]
    assert aangeroepen_met["customer_email"] == "devries@voorbeeld.nl"
    assert aangeroepen_met["success_url"] == "https://app.voorbeeld.nl/signup-gelukt.html"
    assert aangeroepen_met["cancel_url"] == "https://app.voorbeeld.nl/signup.html"
    assert aangeroepen_met["subscription_data"] == {"trial_period_days": 7}
    assert aangeroepen_met["metadata"] == {"aanmelding_id": "42"}


def test_maak_checkout_sessie_zonder_proefperiode_stuurt_geen_trial_period_days(monkeypatch):
    aangeroepen_met = {}

    def _nep_create(**kwargs):
        aangeroepen_met.update(kwargs)
        return _NepSessie(id="cs_test_123", url="https://checkout.stripe.com/c/pay/cs_test_123")

    monkeypatch.setattr(betaalintegratie.stripe.checkout.Session, "create", _nep_create)

    betaalintegratie.maak_checkout_sessie(
        stripe_secret_key="sk_test_geheim",
        price_id="price_abc",
        klant_email="devries@voorbeeld.nl",
        success_url="https://app.voorbeeld.nl/signup-gelukt.html",
        cancel_url="https://app.voorbeeld.nl/signup.html",
        metadata={"aanmelding_id": "42"},
        proefperiode_dagen=None,
    )

    assert aangeroepen_met["subscription_data"] == {}


def test_maak_checkout_sessie_met_extra_line_items(monkeypatch):
    aangeroepen_met = {}

    def _nep_create(**kwargs):
        aangeroepen_met.update(kwargs)
        return _NepSessie(id="cs_test_123", url="https://checkout.stripe.com/c/pay/cs_test_123")

    monkeypatch.setattr(betaalintegratie.stripe.checkout.Session, "create", _nep_create)

    betaalintegratie.maak_checkout_sessie(
        stripe_secret_key="sk_test_geheim",
        price_id="price_abc",
        klant_email="devries@voorbeeld.nl",
        success_url="https://app.voorbeeld.nl/signup-gelukt.html",
        cancel_url="https://app.voorbeeld.nl/signup.html",
        metadata={"aanmelding_id": "42"},
        proefperiode_dagen=14,
        extra_line_items=[{"price": "price_extra_lid", "quantity": 2}, {"price": "price_extra_winkel", "quantity": 1}],
    )

    assert aangeroepen_met["line_items"] == [
        {"price": "price_abc", "quantity": 1},
        {"price": "price_extra_lid", "quantity": 2},
        {"price": "price_extra_winkel", "quantity": 1},
    ]


def test_lees_webhook_event_geldige_signature(monkeypatch):
    verwacht_event = {"type": "checkout.session.completed"}

    def _nep_construct_event(payload, sig_header, secret):
        assert payload == b"ruwe-payload"
        assert sig_header == "t=123,v1=geldig"
        assert secret == "whsec_geheim"
        return verwacht_event

    monkeypatch.setattr(betaalintegratie.stripe.Webhook, "construct_event", _nep_construct_event)

    event = betaalintegratie.lees_webhook_event(
        payload=b"ruwe-payload", signature_header="t=123,v1=geldig", webhook_secret="whsec_geheim"
    )

    assert event == verwacht_event


def test_lees_webhook_event_ongeldige_signature_faalt_hard(monkeypatch):
    def _nep_construct_event(payload, sig_header, secret):
        raise stripe.SignatureVerificationError("ongeldig", sig_header)

    monkeypatch.setattr(betaalintegratie.stripe.Webhook, "construct_event", _nep_construct_event)

    with pytest.raises(betaalintegratie.OngeldigeWebhookSignature):
        betaalintegratie.lees_webhook_event(
            payload=b"ruwe-payload", signature_header="t=123,v1=fout", webhook_secret="whsec_geheim"
        )
