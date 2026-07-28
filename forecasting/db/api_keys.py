"""Fase 4: API-keys in de database. Stap 1 migreerde alleen al-gehashte
waarden over uit api_keys.json — hasht nooit zelf een ruwe key opnieuw en
verzint geen nieuw hashformaat; hergebruikt exact wat security/api_keys.py
al doet (PBKDF2-HMAC-SHA256, 600.000 iteraties, per-key salt).
Stap 2 voegt de opzoekfunctie toe die serving/app.py gebruikt om een
inkomende ruwe key te verifiëren én de bijbehorende organisatie te vinden —
hergebruikt security.api_keys.verifieer_key(), verzint geen tweede
verificatielogica."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import api_keys
from security.api_keys import hash_key, verifieer_key


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


def maak_api_key(engine: Engine, organisatie_id: int, naam: str) -> tuple[int, str]:
    """Genereert een nieuwe ruwe API-key, slaat 'm gehasht op en geeft
    (id, ruwe_key) terug — de ruwe waarde wordt precies één keer getoond
    (in de dashboard-UI direct na aanmaken), de database bewaart alleen
    de hash."""
    ruwe_key = f"vk_{secrets.token_urlsafe(32)}"
    hash_hex, salt_hex = hash_key(ruwe_key)
    with engine.begin() as conn:
        key_id = conn.execute(
            api_keys.insert().values(
                organisatie_id=organisatie_id,
                naam=naam,
                hash=hash_hex,
                salt=salt_hex,
                verlopen_op=None,
                actief=True,
                aangemaakt_op=datetime.now(timezone.utc),
            )
        ).inserted_primary_key[0]
    return key_id, ruwe_key


def lijst_api_keys(engine: Engine, organisatie_id: int):
    """Geeft alle keys van een organisatie terug zonder hash/salt — enkel
    de kolommen die een dashboard mag tonen."""
    with engine.connect() as conn:
        return conn.execute(
            select(api_keys.c.id, api_keys.c.naam, api_keys.c.actief, api_keys.c.aangemaakt_op).where(
                api_keys.c.organisatie_id == organisatie_id
            )
        ).all()


def deactiveer_api_key(engine: Engine, organisatie_id: int, key_id: int) -> bool:
    """Zet een key op inactief, alleen als hij bij organisatie_id hoort.
    Geeft False terug bij een onbekende of andermans key — geen wijziging,
    zodat de aanroepende laag hetzelfde 404-gedrag kan geven als bij de
    store_id-isolatie elders in de app."""
    with engine.begin() as conn:
        resultaat = conn.execute(
            api_keys.update()
            .where(api_keys.c.id == key_id, api_keys.c.organisatie_id == organisatie_id)
            .values(actief=False)
        )
    return resultaat.rowcount > 0


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
