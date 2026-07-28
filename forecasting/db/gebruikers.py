"""Fase 4 Stap 3: gebruikersaccounts. Hergebruikt security.api_keys.hash_key()/
verifieer_key() voor wachtwoorden — zelfde PBKDF2-HMAC-SHA256-aanpak,
geen tweede hashformaat. Geen self-service-registratie (beslissing 1 in
FASE4-SAAS-FOUNDATION.md): gebruikers worden handmatig aangemaakt via
db/gebruikers_cli.py, niet via een publiek registratie-endpoint."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.engine import Connection, Engine

from db.schema import gebruikers
from security.api_keys import hash_key, verifieer_key


def maak_gebruiker(engine: Engine, organisatie_id: int, email: str, wachtwoord: str, rol: str = "lid") -> int:
    hash_hex, salt_hex = hash_key(wachtwoord)
    with engine.begin() as conn:
        return conn.execute(
            gebruikers.insert().values(
                organisatie_id=organisatie_id,
                email=email,
                wachtwoord_hash=hash_hex,
                wachtwoord_salt=salt_hex,
                rol=rol,
                actief=True,
                aangemaakt_op=datetime.now(timezone.utc),
            )
        ).inserted_primary_key[0]


def aantal_actieve_gebruikers(engine: Engine, organisatie_id: int) -> int:
    with engine.connect() as conn:
        return conn.execute(
            select(func.count()).select_from(gebruikers).where(
                gebruikers.c.organisatie_id == organisatie_id, gebruikers.c.actief.is_(True)
            )
        ).scalar_one()


def _maak_gebruiker_met_hash_op_connectie(
    conn: Connection, organisatie_id: int, email: str, wachtwoord_hash: str, wachtwoord_salt: str, rol: str
) -> int:
    return conn.execute(
        gebruikers.insert().values(
            organisatie_id=organisatie_id,
            email=email,
            wachtwoord_hash=wachtwoord_hash,
            wachtwoord_salt=wachtwoord_salt,
            rol=rol,
            actief=True,
            aangemaakt_op=datetime.now(timezone.utc),
        )
    ).inserted_primary_key[0]


def maak_gebruiker_met_hash(
    engine: Engine, organisatie_id: int, email: str, wachtwoord_hash: str, wachtwoord_salt: str,
    rol: str = "lid", conn: Optional[Connection] = None,
) -> int:
    """Zelfde als maak_gebruiker(), maar neemt een al-gehashte hash/salt aan
    in plaats van een plaintext wachtwoord. Bestaat voor de self-serve
    signup-flow (Fase 5 NODIG 5): het wachtwoord wordt al bij /signup
    gehasht en opgeslagen in db.aanmeldingen — deze functie zet die hash
    simpelweg over naar een echte gebruikersrij zodra Stripe de betaling
    bevestigt, zonder ooit een plaintext wachtwoord op te slaan of opnieuw
    te hashen.

    conn: optioneel een al-openstaande connectie/transactie, zie
    db.bootstrap.bootstrap_organisatie voor dezelfde reden/patroon."""
    if conn is not None:
        return _maak_gebruiker_met_hash_op_connectie(conn, organisatie_id, email, wachtwoord_hash, wachtwoord_salt, rol)
    with engine.begin() as eigen_conn:
        return _maak_gebruiker_met_hash_op_connectie(
            eigen_conn, organisatie_id, email, wachtwoord_hash, wachtwoord_salt, rol
        )


def email_is_in_gebruik(engine: Engine, email: str) -> bool:
    """Voor de self-serve signup-flow: voorkomt dat iemand een Stripe
    Checkout Session start voor een e-mailadres dat al een account heeft —
    beter om dat vóór de betaling te melden dan pas bij de webhook, waar
    een mislukte aanmelding niet meer terug te draaien is zonder handmatig
    in te grijpen op een al-betaalde Stripe-subscription."""
    with engine.connect() as conn:
        rij = conn.execute(select(gebruikers.c.id).where(gebruikers.c.email == email)).first()
    return rij is not None


def haal_eigenaar_email(engine: Engine, organisatie_id: int) -> Optional[str]:
    """Voor de wekelijkse herbestel-mail (Fase 5 NODIG 3): de eigenaar is
    degene die de herbestel-prijs instelt en verkoopdata uploadt, dus de
    logische ontvanger van een proactieve melding. Geeft None terug als de
    organisatie (nog) geen eigenaar heeft — zou niet moeten voorkomen bij
    een organisatie die via /signup of db/bootstrap.py is aangemaakt, maar
    dit voorkomt een crash i.p.v. een aanname te doen."""
    with engine.connect() as conn:
        rij = conn.execute(
            select(gebruikers.c.email).where(
                gebruikers.c.organisatie_id == organisatie_id, gebruikers.c.rol == "eigenaar",
                gebruikers.c.actief.is_(True),
            )
        ).first()
    return rij.email if rij is not None else None


def vind_gebruiker_id_via_email(engine: Engine, email: str) -> Optional[int]:
    """Voor het aanvragen van een wachtwoord-reset: alleen actieve
    gebruikers kunnen een reset-token krijgen, zelfde 'actief'-filter als
    verifieer_inloggegevens(). De aanroeper (POST /wachtwoord-reset/
    aanvragen) gebruikt None hetzelfde als een gevonden gebruiker af te
    handelen — altijd dezelfde generieke bevestiging teruggeven, nooit
    lekken of een e-mailadres bestaat."""
    with engine.connect() as conn:
        rij = conn.execute(
            select(gebruikers.c.id).where(gebruikers.c.email == email, gebruikers.c.actief.is_(True))
        ).first()
    return rij.id if rij is not None else None


def wijzig_wachtwoord(engine: Engine, gebruiker_id: int, nieuw_wachtwoord: str) -> None:
    hash_hex, salt_hex = hash_key(nieuw_wachtwoord)
    with engine.begin() as conn:
        conn.execute(
            gebruikers.update().where(gebruikers.c.id == gebruiker_id)
            .values(wachtwoord_hash=hash_hex, wachtwoord_salt=salt_hex)
        )


def haal_gebruiker(engine: Engine, gebruiker_id: int, organisatie_id: int):
    """Geeft de gebruikersrij terug, alleen als gebruiker_id bij
    organisatie_id hoort — anders None. Zelfde org-scoping-patroon als
    db.winkels.hoort_store_bij_organisatie(), hier met de volledige rij
    (inclusief rol) i.p.v. een bool, omdat de aanroeper (winkeltoewijzing-
    beheer) de rol nodig heeft."""
    with engine.connect() as conn:
        return conn.execute(
            select(gebruikers).where(
                gebruikers.c.id == gebruiker_id, gebruikers.c.organisatie_id == organisatie_id
            )
        ).first()


def verifieer_inloggegevens(engine: Engine, email: str, wachtwoord: str) -> int | None:
    """Geeft het gebruiker-id terug als email+wachtwoord kloppen en de
    gebruiker actief is, anders None. Lekt nooit of het email-adres bestaat
    via het verschil tussen 'onbekend' en 'fout wachtwoord' — beide geven
    hetzelfde None terug."""
    with engine.connect() as conn:
        rij = conn.execute(
            select(gebruikers).where(gebruikers.c.email == email, gebruikers.c.actief.is_(True))
        ).first()
    if rij is None:
        return None
    if not verifieer_key(wachtwoord, rij.wachtwoord_hash, rij.wachtwoord_salt):
        return None
    return rij.id
