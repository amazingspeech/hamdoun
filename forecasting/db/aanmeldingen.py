"""Fase 5 NODIG 5: self-serve signup. Een aanmelding is de tussentoestand
tussen 'iemand vulde het aanmeldformulier in' en 'de betaling is bevestigd
en de echte organisatie + eigenaar-account bestaan' — zie serving/app.py's
POST /signup en POST /webhooks/stripe."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine

from db.schema import aanmeldingen, organisaties


def maak_aanmelding(
    engine: Engine,
    organisatie_naam: str,
    organisatie_slug: str,
    email: str,
    wachtwoord_hash: str,
    wachtwoord_salt: str,
    stripe_checkout_session_id: str,
    kvk_nummer: str,
    aantal_leden: int,
    aantal_winkels: int,
    was_kvk_herhaling: bool,
) -> int:
    with engine.begin() as conn:
        return conn.execute(
            aanmeldingen.insert().values(
                organisatie_naam=organisatie_naam,
                organisatie_slug=organisatie_slug,
                email=email,
                wachtwoord_hash=wachtwoord_hash,
                wachtwoord_salt=wachtwoord_salt,
                stripe_checkout_session_id=stripe_checkout_session_id,
                kvk_nummer=kvk_nummer,
                aantal_leden=aantal_leden,
                aantal_winkels=aantal_winkels,
                was_kvk_herhaling=was_kvk_herhaling,
                organisatie_id=None,
                voltooid_op=None,
                aangemaakt_op=datetime.now(timezone.utc),
            )
        ).inserted_primary_key[0]


def haal_aanmelding_bij_sessie(engine: Engine, stripe_checkout_session_id: str):
    with engine.connect() as conn:
        return conn.execute(
            select(aanmeldingen).where(aanmeldingen.c.stripe_checkout_session_id == stripe_checkout_session_id)
        ).first()


def _voltooi_aanmelding_op_connectie(conn: Connection, aanmelding_id: int, organisatie_id: int) -> None:
    conn.execute(
        aanmeldingen.update()
        .where(aanmeldingen.c.id == aanmelding_id)
        .values(organisatie_id=organisatie_id, voltooid_op=datetime.now(timezone.utc))
    )


def voltooi_aanmelding(
    engine: Engine, aanmelding_id: int, organisatie_id: int, conn: Optional[Connection] = None
) -> None:
    """conn: optioneel een al-openstaande connectie/transactie, zie
    db.bootstrap.bootstrap_organisatie voor dezelfde reden/patroon."""
    if conn is not None:
        _voltooi_aanmelding_op_connectie(conn, aanmelding_id, organisatie_id)
        return
    with engine.begin() as eigen_conn:
        _voltooi_aanmelding_op_connectie(eigen_conn, aanmelding_id, organisatie_id)


def _basis_slug(naam: str) -> str:
    naam = naam.strip().lower()
    naam = naam.replace("é", "e").replace("è", "e").replace("ë", "e").replace("ï", "i")
    naam = re.sub(r"[^a-z0-9]+", "-", naam)
    return naam.strip("-")


def genereer_unieke_organisatie_slug(engine: Engine, organisatie_naam: str) -> str:
    """Twee klanten kunnen dezelfde bedrijfsnaam invullen — organisaties.slug
    is uniek (zie db/schema.py, beslissing 4), dus deze functie wijkt uit
    naar '-2', '-3', enz. Kijkt zowel naar al-bestaande organisaties als naar
    nog-niet-voltooide aanmeldingen, zodat een botsing al bij /signup wordt
    opgelost — niet pas bij de webhook, ná de betaling, waar een mislukte
    organisatie-insert veel vervelender is om recht te zetten."""
    basis = _basis_slug(organisatie_naam)
    with engine.connect() as conn:
        bestaande_organisatie_slugs = {r[0] for r in conn.execute(select(organisaties.c.slug))}
        openstaande_aanmelding_slugs = {
            r[0] for r in conn.execute(
                select(aanmeldingen.c.organisatie_slug).where(aanmeldingen.c.organisatie_id.is_(None))
            )
        }
    bezet = bestaande_organisatie_slugs | openstaande_aanmelding_slugs

    if basis not in bezet:
        return basis
    volgnummer = 2
    while f"{basis}-{volgnummer}" in bezet:
        volgnummer += 1
    return f"{basis}-{volgnummer}"
