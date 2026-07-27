"""Fase 5 NODIG 5 (aanvulling, 2026-07-27): een self-serve organisatie
heeft geen enkele winkel in het gedeelde, op Rossmann-data getrainde model
(serving.forecast.voorspel_periode faalt hard op een onbekend store_id) —
er is geen manier om een gloednieuwe zaak alsnog in dat model te krijgen.
Deze module berekent in plaats daarvan een lichte, eerlijke voorspelling
rechtstreeks uit de eigen geüploade verkoopdata (db.verkoopdata) via een
naïef dag-van-de-week-gemiddelde. Bewust geen ML-model: te weinig data per
klant om overfitting te vermijden, en een simpele, uitlegbare methode past
beter bij 'nooit een te precies getal verzinnen' dan een zwaar model dat
op een handvol weken data evengoed ruis zou aanleren."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean
from typing import Optional

import numpy as np

# Onder dit aantal dagen is een dag-van-de-week-patroon te wankel om te
# tonen (bij 28 dagen is elke weekdag minstens 4x gezien) — zie de
# afweging met de gebruiker: sneller een getal tonen op minder data zou
# precies het soort valse precisie zijn dat dit product overal elders
# bewust vermijdt.
MINIMUM_DAGEN = 28


def bereken_eigen_voorspelling(rijen: list[dict], horizon_dagen: int, vanaf: date) -> Optional[dict]:
    """rijen: [{"datum": "JJJJ-MM-DD", "omzet": float}, ...], zoals
    db.verkoopdata.haal_verkoopdata() teruggeeft. Geeft None als er nog
    geen MINIMUM_DAGEN historie is. p50 per dag is het historische
    gemiddelde voor die weekdag; p10/p90 komen uit het 10e/90e percentiel
    van de werkelijke afwijkingen (actual - eigen-weekdaggemiddelde) over
    de hele historie — dus een echte, uit de eigen data afgeleide
    bandbreedte, geen aangenomen percentage."""
    if len(rijen) < MINIMUM_DAGEN:
        return None

    per_weekday: dict[int, list[float]] = defaultdict(list)
    for rij in rijen:
        d = date.fromisoformat(rij["datum"])
        per_weekday[d.weekday()].append(rij["omzet"])
    weekday_gemiddelde = {wd: mean(waarden) for wd, waarden in per_weekday.items()}

    residuen = [
        rij["omzet"] - weekday_gemiddelde[date.fromisoformat(rij["datum"]).weekday()] for rij in rijen
    ]
    p10_residu = float(np.percentile(residuen, 10))
    p90_residu = float(np.percentile(residuen, 90))

    voorspellingen = []
    for i in range(horizon_dagen):
        d = vanaf + timedelta(days=i)
        basis = weekday_gemiddelde.get(d.weekday())
        if basis is None:
            # Deze weekdag komt niet voor in de geüploade historie (bv. een
            # zaak die nooit op zondag open is) — geen basis om op te
            # voorspellen, dan liever 0 tonen dan verzinnen.
            basis = 0.0
        p50 = max(basis, 0.0)
        p10 = max(min(basis + p10_residu, p50), 0.0)
        p90 = max(basis + p90_residu, p50)
        voorspellingen.append({"datum": d.isoformat(), "p10": p10, "p50": p50, "p90": p90})

    return {
        "voorspellingen": voorspellingen,
        "totaal_p10": sum(v["p10"] for v in voorspellingen),
        "totaal_p50": sum(v["p50"] for v in voorspellingen),
        "totaal_p90": sum(v["p90"] for v in voorspellingen),
    }
