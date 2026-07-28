"""Fase 5 premium: herbestel-advies per product, alleen voor self-serve
organisaties met eigen per-product verkoopdata (db/product_verkoopdata.py)
— nooit voor het gedeelde Rossmann-model, dat geen product-dimensie heeft.
Zelfde naïeve dag-van-de-week-methode als serving/eigen_voorspelling.py
(bewust geen ML-model, zelfde reden), toegepast per product afzonderlijk
en direct in aantal stuks — geen prijs-omrekening nodig."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

import numpy as np

# Zelfde drempel en redenering als serving.eigen_voorspelling.MINIMUM_DAGEN
# (elke weekdag minstens 4x gezien) — hier per product toegepast, niet per
# organisatie: elk product heeft zijn eigen historielengte nodig, ongeacht
# hoe lang de organisatie als geheel al uploadt.
MINIMUM_DAGEN = 28


def _bereken_voor_een_product(rijen: list[dict], horizon_dagen: int, vanaf: date) -> dict | None:
    """rijen: alle {"datum", "aantal"}-rijen van precies één product.
    Geeft None als er nog geen MINIMUM_DAGEN historie is voor dit product."""
    if len(rijen) < MINIMUM_DAGEN:
        return None

    per_weekday: dict[int, list[float]] = defaultdict(list)
    for rij in rijen:
        d = date.fromisoformat(rij["datum"])
        per_weekday[d.weekday()].append(rij["aantal"])
    weekday_gemiddelde = {wd: mean(waarden) for wd, waarden in per_weekday.items()}

    residuen = [rij["aantal"] - weekday_gemiddelde[date.fromisoformat(rij["datum"]).weekday()] for rij in rijen]
    p10_residu = float(np.percentile(residuen, 10))
    p90_residu = float(np.percentile(residuen, 90))

    totaal_p10 = totaal_p50 = totaal_p90 = 0.0
    for i in range(horizon_dagen):
        d = vanaf + timedelta(days=i)
        basis = weekday_gemiddelde.get(d.weekday(), 0.0)
        p50 = max(basis, 0.0)
        p10 = max(min(basis + p10_residu, p50), 0.0)
        p90 = max(basis + p90_residu, p50)
        totaal_p10 += p10
        totaal_p50 += p50
        totaal_p90 += p90

    return {"aantal_p10": totaal_p10, "aantal_p50": totaal_p50, "aantal_p90": totaal_p90}


def bereken_herbestel_advies_per_product(rijen: list[dict], horizon_dagen: int, vanaf: date) -> list[dict]:
    """rijen: [{"datum": "JJJJ-MM-DD", "product": str, "aantal": int}, ...],
    zoals db.product_verkoopdata.haal_product_verkoopdata() teruggeeft.
    Groepeert per product, slaat producten met minder dan MINIMUM_DAGEN
    eigen historie stilzwijgend over (liever niets tonen dan een
    onbetrouwbaar getal), en sorteert de rest aflopend op verwacht aantal
    — de producten die het meest bijbestellen nodig hebben staan bovenaan."""
    per_product: dict[str, list[dict]] = defaultdict(list)
    for rij in rijen:
        per_product[rij["product"]].append(rij)

    resultaten = []
    for product, product_rijen in per_product.items():
        advies = _bereken_voor_een_product(product_rijen, horizon_dagen, vanaf)
        if advies is None:
            continue
        resultaten.append({"product": product, **advies})

    resultaten.sort(key=lambda r: r["aantal_p50"], reverse=True)
    return resultaten
