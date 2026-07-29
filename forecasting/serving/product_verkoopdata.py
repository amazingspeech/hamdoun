"""Fase 5 premium (herbestel-advies per product): CSV-parser voor
per-product verkoopdata. Zelfde stijl als serving/verkoopdata.py, maar met
een product-kolom en aantal-stuks i.p.v. omzet — geen prijs-omrekening
nodig voor een stuksadvies. Vereist een rij per product per dag (ook bij
0 verkocht), zie db/schema.py's toelichting bij eigen_product_verkoopdata
— zonder expliciete nul-rijen zou het dag-van-de-week-gemiddelde
structureel te hoog uitvallen."""
from __future__ import annotations

import csv
import io
from datetime import date as _date

VERPLICHTE_KOLOMMEN = {"datum", "product", "aantal"}


class OngeldigeProductVerkoopdata(Exception):
    pass


def _detecteer_scheidingsteken(inhoud: str) -> str:
    """Herkent ',' of ';' als kolomscheidingsteken (Nederlandse/EU CSV-
    exports gebruiken vaak ';'). Valt terug op ',' als er niets
    herkenbaars in de kopregel staat."""
    kopregel = inhoud.split("\n", 1)[0]
    try:
        return csv.Sniffer().sniff(kopregel, delimiters=",;").delimiter
    except csv.Error:
        return ","


def parse_product_verkoopdata_csv(inhoud: str) -> list[tuple[str, str, int]]:
    """Leest een CSV met kolommen datum,product,aantal (kolomnamen
    hoofdletter-ongevoelig, scheidingsteken ',' of ';') en geeft
    (datum-string, product, aantal) per rij terug, gesorteerd zoals ze in
    het bestand staan. Faalt hard — nooit een rij stilzwijgend overslaan —
    bij ontbrekende kolommen, een ongeldige datum, een lege productnaam,
    een ongeldig/negatief/niet-heel aantal, of een dubbele
    datum+product-combinatie."""
    lezer = csv.DictReader(io.StringIO(inhoud), delimiter=_detecteer_scheidingsteken(inhoud))
    kolommen = {(naam or "").strip().lower() for naam in (lezer.fieldnames or [])}
    if not VERPLICHTE_KOLOMMEN <= kolommen:
        raise OngeldigeProductVerkoopdata(
            f"CSV mist verplichte kolommen: verwacht 'datum', 'product' en 'aantal', gevonden {sorted(kolommen)}."
        )

    veld_datum = next(n for n in lezer.fieldnames if n.strip().lower() == "datum")
    veld_product = next(n for n in lezer.fieldnames if n.strip().lower() == "product")
    veld_aantal = next(n for n in lezer.fieldnames if n.strip().lower() == "aantal")

    resultaten: list[tuple[str, str, int]] = []
    geziene_combinaties: set[tuple[str, str]] = set()
    for regelnummer, rij in enumerate(lezer, start=2):
        ruwe_datum = (rij.get(veld_datum) or "").strip()
        product = (rij.get(veld_product) or "").strip()
        ruwe_aantal = (rij.get(veld_aantal) or "").strip()

        if len(ruwe_datum) != 10 or ruwe_datum[4] != "-" or ruwe_datum[7] != "-":
            raise OngeldigeProductVerkoopdata(
                f"Regel {regelnummer}: ongeldige datum '{ruwe_datum}', verwacht JJJJ-MM-DD."
            )
        try:
            jaar, maand, dag = int(ruwe_datum[:4]), int(ruwe_datum[5:7]), int(ruwe_datum[8:10])
            _date(jaar, maand, dag)
        except ValueError:
            raise OngeldigeProductVerkoopdata(
                f"Regel {regelnummer}: ongeldige datum '{ruwe_datum}', verwacht JJJJ-MM-DD."
            )

        if not product:
            raise OngeldigeProductVerkoopdata(f"Regel {regelnummer}: productnaam mag niet leeg zijn.")

        try:
            aantal = int(ruwe_aantal)
        except ValueError:
            raise OngeldigeProductVerkoopdata(f"Regel {regelnummer}: ongeldig aantal '{ruwe_aantal}', verwacht een heel getal.")
        if aantal < 0:
            raise OngeldigeProductVerkoopdata(f"Regel {regelnummer}: aantal mag niet negatief zijn ({aantal}).")

        combinatie = (ruwe_datum, product)
        if combinatie in geziene_combinaties:
            raise OngeldigeProductVerkoopdata(f"Regel {regelnummer}: dubbele datum+product-combinatie '{ruwe_datum}, {product}'.")
        geziene_combinaties.add(combinatie)

        resultaten.append((ruwe_datum, product, aantal))

    return resultaten
