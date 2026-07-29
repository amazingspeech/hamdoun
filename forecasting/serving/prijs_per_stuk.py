"""Automatische afleiding van de gemiddelde omzet per verkocht stuk uit
twee al bestaande, per eigen winkel geüploade datasets — zie
docs/superpowers/specs/2026-07-29-eigen-winkels-design.md sectie 3.
Losstaande, puur-functionele module (geen DB-toegang), zelfde stijl als
serving/verkoopdata.py."""
from __future__ import annotations

from collections import defaultdict
from typing import Optional


def bereken_gemiddelde_prijs_per_stuk(
    verkoopdata_rijen: list[dict], product_verkoopdata_rijen: list[dict]
) -> Optional[float]:
    """Sommeert omzet en aantal, uitsluitend over de datums die in beide
    sets voorkomen, en deelt de twee totalen. None zonder overlap of bij
    een totaal aantal van 0 — nooit een prijs verzinnen of door 0 delen."""
    aantal_per_datum: dict[str, int] = defaultdict(int)
    for rij in product_verkoopdata_rijen:
        aantal_per_datum[rij["datum"]] += rij["aantal"]

    totaal_omzet = 0.0
    totaal_aantal = 0
    for rij in verkoopdata_rijen:
        if rij["datum"] not in aantal_per_datum:
            continue
        totaal_omzet += rij["omzet"]
        totaal_aantal += aantal_per_datum[rij["datum"]]

    if totaal_aantal <= 0:
        return None
    return totaal_omzet / totaal_aantal
