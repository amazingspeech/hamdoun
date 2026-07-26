"""Fase 4 Stap 3: server-side sessiebeheer. Sessietokens worden met een
snelle SHA-256-hash opgeslagen, niet met de trage PBKDF2 uit
security/api_keys.py — dat verschil is bewust: PBKDF2's trage, herhaalde
hashing bestaat om laag-entropie geheimen (wachtwoorden, mensgekozen
API-keys) tegen brute-force te beschermen. Een sessietoken is zelf al een
willekeurige, hoge-entropie waarde (secrets.token_urlsafe), dus een snelle
hash volstaat om 'm nooit in leesbare vorm in de database te hoeven
bewaren."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import sessies

STANDAARD_GELDIGHEIDSDUUR = timedelta(days=7)


def _hash_token(ruwe_token: str) -> str:
    return hashlib.sha256(ruwe_token.encode("utf-8")).hexdigest()


def _als_utc(moment: datetime) -> datetime:
    """SQLite/SQLAlchemy geeft datetimes terug zonder tijdzone-info, ook al
    is er altijd UTC ingeschreven — hier expliciet weer UTC van maken
    vóór vergelijking, in plaats van stilzwijgend een naive/aware-mismatch
    te riskeren."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def maak_sessie(engine: Engine, gebruiker_id: int, geldigheidsduur: timedelta = STANDAARD_GELDIGHEIDSDUUR) -> str:
    """Maakt een nieuwe sessie aan en geeft de ruwe token terug — die wordt
    precies één keer getoond (in de login-response als cookie-waarde), de
    database bewaart alleen de hash."""
    ruwe_token = secrets.token_urlsafe(32)
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            sessies.insert().values(
                gebruiker_id=gebruiker_id,
                token_hash=_hash_token(ruwe_token),
                aangemaakt_op=nu,
                verloopt_op=nu + geldigheidsduur,
            )
        )
    return ruwe_token


def vind_gebruiker_voor_sessie(engine: Engine, ruwe_token: str) -> int | None:
    with engine.connect() as conn:
        rij = conn.execute(
            select(sessies.c.gebruiker_id, sessies.c.verloopt_op).where(
                sessies.c.token_hash == _hash_token(ruwe_token)
            )
        ).first()
    if rij is None:
        return None
    if _als_utc(rij.verloopt_op) < datetime.now(timezone.utc):
        return None
    return rij.gebruiker_id


def verwijder_sessie(engine: Engine, ruwe_token: str) -> None:
    with engine.begin() as conn:
        conn.execute(sessies.delete().where(sessies.c.token_hash == _hash_token(ruwe_token)))
