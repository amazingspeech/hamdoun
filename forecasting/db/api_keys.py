"""Fase 4: API-keys in de database. Stap 1 migreerde alleen al-gehashte
waarden over uit api_keys.json — hasht nooit zelf een ruwe key opnieuw en
verzint geen nieuw hashformaat; hergebruikt exact wat security/api_keys.py
al doet (PBKDF2-HMAC-SHA256, 600.000 iteraties, per-key salt).
Stap 2 voegt de opzoekfunctie toe die serving/app.py gebruikt om een
inkomende ruwe key te verifiëren én de bijbehorende organisatie te vinden —
hergebruikt security.api_keys.verifieer_key(), verzint geen tweede
verificatielogica."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import api_keys
from security.api_keys import verifieer_key


def migreer_bestaande_key(engine: Engine, organisatie_id: int, naam: str, hash: str, salt: str) -> int:
    """Zet één reeds-gehashte key (zoals opgeslagen in api_keys.json) over
    naar de database, gekoppeld aan organisatie_id. Geeft het nieuwe
    rij-id terug."""
    with engine.begin() as conn:
        return conn.execute(
            api_keys.insert().values(
                organisatie_id=organisatie_id,
                naam=naam,
                hash=hash,
                salt=salt,
                verlopen_op=None,
                actief=True,
                aangemaakt_op=datetime.now(timezone.utc),
            )
        ).inserted_primary_key[0]


def vind_organisatie_voor_key(engine: Engine, ruwe_key: str) -> tuple[str, int] | None:
    """Zoekt welke actieve key overeenkomt met ruwe_key en geeft
    (naam, organisatie_id) terug, of None als geen enkele actieve key
    matcht. Zelfde lineaire scan-en-verifieer-patroon als
    security.api_keys.vind_key_naam(), nu tegen databaserijen i.p.v. een
    JSON-dict."""
    with engine.connect() as conn:
        for rij in conn.execute(select(api_keys).where(api_keys.c.actief.is_(True))):
            if verifieer_key(ruwe_key, rij.hash, rij.salt):
                return rij.naam, rij.organisatie_id
    return None
