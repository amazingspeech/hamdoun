"""Stap 1 (Fase 4): API-keys in de database. Migreert alleen al-gehashte
waarden over uit api_keys.json — hasht nooit zelf een ruwe key opnieuw en
verzint geen nieuw hashformaat; hergebruikt exact wat security/api_keys.py
al doet (PBKDF2-HMAC-SHA256, 600.000 iteraties, per-key salt).

Nog niet aangesloten op serving/app.py: de draaiende API leest nog steeds
api_keys.json. Dat is bewust (zie FASE4-SAAS-FOUNDATION.md, Stap 2 is de
eerste stap die gedrag verandert) — dit bestand bevat alleen de
migratie-tooling."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.engine import Engine

from db.schema import api_keys


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
