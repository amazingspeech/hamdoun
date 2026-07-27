"""Fase 4 Stap 4: wachtwoord-reset. Zelfde token-aanpak als db/sessies.py —
SHA-256 op een hoge-entropie secrets.token_urlsafe-waarde, geen PBKDF2 (die
bestaat om laag-entropie geheimen tegen brute-force te beschermen, dat
probeert hier niemand te raden). Bewust een eigen, kortere geldigheidsduur
en eenmalig-gebruik-vlag (gebruikt_op) — een reset-token geeft toegang tot
een gevoeligere actie dan een sessietoken."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import wachtwoord_reset_tokens

STANDAARD_GELDIGHEIDSDUUR = timedelta(hours=1)


def _hash_token(ruwe_token: str) -> str:
    return hashlib.sha256(ruwe_token.encode("utf-8")).hexdigest()


def _als_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def maak_reset_token(engine: Engine, gebruiker_id: int, geldigheidsduur: timedelta = STANDAARD_GELDIGHEIDSDUUR) -> str:
    ruwe_token = secrets.token_urlsafe(32)
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            wachtwoord_reset_tokens.insert().values(
                gebruiker_id=gebruiker_id,
                token_hash=_hash_token(ruwe_token),
                aangemaakt_op=nu,
                verloopt_op=nu + geldigheidsduur,
                gebruikt_op=None,
            )
        )
    return ruwe_token


def vind_gebruiker_voor_reset_token(engine: Engine, ruwe_token: str) -> Optional[int]:
    with engine.connect() as conn:
        rij = conn.execute(
            select(wachtwoord_reset_tokens.c.gebruiker_id, wachtwoord_reset_tokens.c.verloopt_op,
                   wachtwoord_reset_tokens.c.gebruikt_op)
            .where(wachtwoord_reset_tokens.c.token_hash == _hash_token(ruwe_token))
        ).first()
    if rij is None:
        return None
    if rij.gebruikt_op is not None:
        return None
    if _als_utc(rij.verloopt_op) < datetime.now(timezone.utc):
        return None
    return rij.gebruiker_id


def markeer_reset_token_gebruikt(engine: Engine, ruwe_token: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            wachtwoord_reset_tokens.update()
            .where(wachtwoord_reset_tokens.c.token_hash == _hash_token(ruwe_token))
            .values(gebruikt_op=datetime.now(timezone.utc))
        )
