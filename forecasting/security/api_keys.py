"""API-key-beheer: keys worden nooit in platte tekst opgeslagen, alleen als
PBKDF2-HMAC-SHA256-hash met een per-key unieke salt — zelfde aanpak als
Certo's wachtwoordhashing. Zo kan één klantintegratie worden ingetrokken
zonder de rest te raken."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

HASH_ITERATIES = 600_000


def hash_key(ruwe_key: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", ruwe_key.encode("utf-8"), salt, HASH_ITERATIES, dklen=32)
    return digest.hex(), salt.hex()


def verifieer_key(ruwe_key: str, hash_hex: str, salt_hex: str) -> bool:
    try:
        berekend, _ = hash_key(ruwe_key, bytes.fromhex(salt_hex))
    except (ValueError, TypeError):
        return False
    return secrets.compare_digest(berekend, hash_hex)


def laad_keys(pad: Path) -> dict:
    if not pad.exists():
        return {}
    return json.loads(pad.read_text(encoding="utf-8"))


def voeg_key_toe(pad: Path, naam: str, ruwe_key: str) -> None:
    keys = laad_keys(pad)
    hash_hex, salt_hex = hash_key(ruwe_key)
    keys[naam] = {"hash": hash_hex, "salt": salt_hex}
    pad.write_text(json.dumps(keys, indent=2), encoding="utf-8")
    try:
        os.chmod(pad, 0o600)
    except OSError:
        pass


def vind_key_naam(pad: Path, ruwe_key: str) -> str | None:
    """Zoekt welke genoemde key overeenkomt met ruwe_key. Geeft None terug
    als geen enkele overeenkomt (of het bestand leeg/ontbrekend is)."""
    keys = laad_keys(pad)
    for naam, info in keys.items():
        if verifieer_key(ruwe_key, info["hash"], info["salt"]):
            return naam
    return None
