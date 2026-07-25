"""Versleuteling in rust voor de forecasting-toolkit's audit-log en
modelartefacten.

AES-256-GCM via de cryptography-package: authenticated encryption — een
gewijzigd of corrupt bestand geeft bij het ontsleutelen een harde fout
(InvalidTag) in plaats van stilzwijgend verkeerde data.

Direct afgeleid van Certo's encryptie.py (protocolchecker-project): zelfde
algoritme, zelfde hard-fail-op-ontbrekende-sleutel-filosofie.

Sleutel genereren:  python3 -m security.encryptie genereer-sleutel
"""
from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path

from cryptography.exceptions import InvalidTag  # noqa: F401 (voor aanroepers die 'm willen vangen)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SLEUTEL_ENV_VAR = "FORECASTING_ENCRYPTIE_SLEUTEL"
SLEUTEL_LENGTE = 32  # AES-256
NONCE_LENGTE = 12
MAGIC = b"TSRFCST1"

_sleutel_cache: bytes | None = None


def laad_sleutel() -> bytes:
    """Leest en cachet de encryptiesleutel uit de omgeving. Faalt hard als de
    sleutel ontbreekt of de verkeerde lengte heeft — nooit een stille
    fallback, dat zou onopgemerkt tot onleesbare data leiden."""
    global _sleutel_cache
    if _sleutel_cache is not None:
        return _sleutel_cache

    ruw = os.environ.get(SLEUTEL_ENV_VAR)
    if not ruw:
        raise RuntimeError(
            f"{SLEUTEL_ENV_VAR} ontbreekt in de omgeving. Genereer een sleutel met:\n"
            "    python3 -m security.encryptie genereer-sleutel"
        )
    try:
        sleutel = base64.b64decode(ruw, validate=True)
    except Exception as e:
        raise RuntimeError(f"{SLEUTEL_ENV_VAR} is geen geldige base64-waarde: {e}")
    if len(sleutel) != SLEUTEL_LENGTE:
        raise RuntimeError(
            f"{SLEUTEL_ENV_VAR} moet {SLEUTEL_LENGTE} bytes zijn na base64-decodering, "
            f"kreeg {len(sleutel)}."
        )
    _sleutel_cache = sleutel
    return sleutel


def genereer_sleutel() -> str:
    """Genereert een nieuwe willekeurige sleutel, als base64-string."""
    return base64.b64encode(secrets.token_bytes(SLEUTEL_LENGTE)).decode("ascii")


def versleutel(data: bytes, sleutel: bytes | None = None) -> bytes:
    if sleutel is None:
        sleutel = laad_sleutel()
    nonce = os.urandom(NONCE_LENGTE)
    ciphertext = AESGCM(sleutel).encrypt(nonce, data, None)
    return nonce + ciphertext


def ontsleutel(data: bytes, sleutel: bytes | None = None) -> bytes:
    if sleutel is None:
        sleutel = laad_sleutel()
    nonce, ciphertext = data[:NONCE_LENGTE], data[NONCE_LENGTE:]
    return AESGCM(sleutel).decrypt(nonce, ciphertext, None)


def schrijf_bestand(pad: Path, data: bytes) -> None:
    """Versleutelt en schrijft data weg, met MAGIC-kop en chmod 600."""
    pad.write_bytes(MAGIC + versleutel(data))
    try:
        os.chmod(pad, 0o600)
    except OSError:
        pass


def lees_bestand(pad: Path) -> bytes:
    """Leest en ontsleutelt een bestand geschreven met schrijf_bestand()."""
    ruw = pad.read_bytes()
    if not ruw.startswith(MAGIC):
        raise RuntimeError(f"{pad} staat niet in het verwachte versleutelde formaat.")
    return ontsleutel(ruw[len(MAGIC):])


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "genereer-sleutel":
        print(genereer_sleutel())
    else:
        print("Gebruik: python3 -m security.encryptie genereer-sleutel")
