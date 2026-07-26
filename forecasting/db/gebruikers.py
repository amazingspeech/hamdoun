"""Fase 4 Stap 3: gebruikersaccounts. Hergebruikt security.api_keys.hash_key()/
verifieer_key() voor wachtwoorden — zelfde PBKDF2-HMAC-SHA256-aanpak,
geen tweede hashformaat. Geen self-service-registratie (beslissing 1 in
FASE4-SAAS-FOUNDATION.md): gebruikers worden handmatig aangemaakt via
db/gebruikers_cli.py, niet via een publiek registratie-endpoint."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

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
