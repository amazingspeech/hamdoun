"""Audit-logging voor de forecasting-API: staat altijd aan (wie vroeg wat,
wanneer), alleen de versleuteling ervan is toggle-baar via config. Elke regel
heeft zijn eigen nonce, dus toevoegen hoeft nooit het hele bestand te lezen."""
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

from security import encryptie


def log(pad: Path, event: dict, versleuteld: bool) -> None:
    """Voegt één regel toe aan het audit-logbestand. `event` bevat nooit
    ruwe gevoelige payloads, alleen metadata (key-naam, store_id, horizon,
    statuscode, latency)."""
    regel = {"tijdstip": time.time(), **event}
    plat = json.dumps(regel, ensure_ascii=False)

    bestond_al = pad.exists()
    with pad.open("a", encoding="utf-8") as f:
        if versleuteld:
            f.write(base64.b64encode(encryptie.versleutel(plat.encode("utf-8"))).decode("ascii") + "\n")
        else:
            f.write(plat + "\n")

    if not bestond_al:
        try:
            os.chmod(pad, 0o600)
        except OSError:
            pass
