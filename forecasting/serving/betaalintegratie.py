"""Fase 5 NODIG 5: dunne wrapper rond de Stripe SDK voor de self-serve
signup-flow (zie serving/app.py's POST /signup en POST /webhooks/stripe).
Zelfde stijl als security/mail.py — expliciete primitieve parameters, geen
koppeling aan serving.config, en de api_key wordt per aanroep meegegeven
(niet als globale stripe.api_key) zodat er geen gedeelde mutable state is
tussen requests of tests."""
from __future__ import annotations

from typing import NamedTuple

import stripe


class OngeldigeWebhookSignature(Exception):
    pass


class CheckoutSessie(NamedTuple):
    id: str
    checkout_url: str


def maak_checkout_sessie(
    stripe_secret_key: str,
    price_id: str,
    klant_email: str,
    success_url: str,
    cancel_url: str,
    metadata: dict,
    proefperiode_dagen: int,
) -> CheckoutSessie:
    sessie = stripe.checkout.Session.create(
        api_key=stripe_secret_key,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=klant_email,
        success_url=success_url,
        cancel_url=cancel_url,
        subscription_data={"trial_period_days": proefperiode_dagen},
        metadata=metadata,
    )
    return CheckoutSessie(id=sessie.id, checkout_url=sessie.url)


def lees_webhook_event(payload: bytes, signature_header: str, webhook_secret: str):
    """Verifieert dat het event echt van Stripe komt (HMAC-signature met de
    webhook-secret) vóórdat de inhoud vertrouwd wordt — zonder dit zou
    iedereen die de URL kent een nep-'betaling geslaagd'-event kunnen
    versturen en zo een gratis organisatie aanmaken."""
    try:
        return stripe.Webhook.construct_event(payload, signature_header, webhook_secret)
    except (ValueError, stripe.SignatureVerificationError) as e:
        raise OngeldigeWebhookSignature(str(e)) from e
