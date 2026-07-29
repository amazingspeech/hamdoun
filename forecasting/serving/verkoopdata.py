"""Fase 5 NODIG 2 (afgeslankt): eigen verkoopdata uploaden via het
dashboard, i.p.v. een live Shopify/WooCommerce-koppeling of een handmatige
operator-snapshot. Geeft een winkelier zonder platform-koppeling toch een
manier om hun eigen verkoophistorie te zien in het dashboard. Voedt
(bewust, voorlopig) geen voorspelling — dat vereist eerst een aparte
afweging over modelvaliditeit voor winkels buiten het Rossmann-getrainde
domein, zie forecasting_toolkit_audit_roadmap-memo."""
from __future__ import annotations

import csv
import io
from datetime import date as _date

VERPLICHTE_KOLOMMEN = {"datum", "omzet"}


class OngeldigeVerkoopdata(Exception):
    pass


def _detecteer_scheidingsteken(inhoud: str) -> str:
    """Herkent ',' of ';' als kolomscheidingsteken (Nederlandse/EU CSV-
    exports, bv. uit een bankrekening, gebruiken vaak ';'). Valt terug op
    ',' als er niets herkenbaars in de kopregel staat."""
    kopregel = inhoud.split("\n", 1)[0]
    try:
        return csv.Sniffer().sniff(kopregel, delimiters=",;").delimiter
    except csv.Error:
        return ","


def parse_verkoopdata_csv(inhoud: str) -> list[tuple[str, float]]:
    """Leest een CSV met kolommen datum,omzet (kolomnamen hoofdletter-
    ongevoelig, scheidingsteken ',' of ';') en geeft (datum-string, omzet)
    per rij terug, gesorteerd zoals ze in het bestand staan. Faalt hard —
    nooit een rij stilzwijgend overslaan — bij ontbrekende kolommen, een
    ongeldige datum, een ongeldig of negatief omzetgetal, of een dubbele
    datum."""
    lezer = csv.DictReader(io.StringIO(inhoud), delimiter=_detecteer_scheidingsteken(inhoud))
    kolommen = {(naam or "").strip().lower() for naam in (lezer.fieldnames or [])}
    if not VERPLICHTE_KOLOMMEN <= kolommen:
        raise OngeldigeVerkoopdata(
            f"CSV mist verplichte kolommen: verwacht 'datum' en 'omzet', gevonden {sorted(kolommen)}."
        )

    veld_datum = next(n for n in lezer.fieldnames if n.strip().lower() == "datum")
    veld_omzet = next(n for n in lezer.fieldnames if n.strip().lower() == "omzet")

    resultaten: list[tuple[str, float]] = []
    geziene_datums: set[str] = set()
    for regelnummer, rij in enumerate(lezer, start=2):
        ruwe_datum = (rij.get(veld_datum) or "").strip()
        ruwe_omzet = (rij.get(veld_omzet) or "").strip()

        if len(ruwe_datum) != 10 or ruwe_datum[4] != "-" or ruwe_datum[7] != "-":
            raise OngeldigeVerkoopdata(f"Regel {regelnummer}: ongeldige datum '{ruwe_datum}', verwacht JJJJ-MM-DD.")
        try:
            jaar, maand, dag = int(ruwe_datum[:4]), int(ruwe_datum[5:7]), int(ruwe_datum[8:10])
            _date(jaar, maand, dag)
        except ValueError:
            raise OngeldigeVerkoopdata(f"Regel {regelnummer}: ongeldige datum '{ruwe_datum}', verwacht JJJJ-MM-DD.")

        try:
            omzet = float(ruwe_omzet)
        except ValueError:
            raise OngeldigeVerkoopdata(f"Regel {regelnummer}: ongeldig omzetgetal '{ruwe_omzet}'.")
        if omzet < 0:
            raise OngeldigeVerkoopdata(f"Regel {regelnummer}: omzet mag niet negatief zijn ({omzet}).")

        if ruwe_datum in geziene_datums:
            raise OngeldigeVerkoopdata(f"Regel {regelnummer}: dubbele datum '{ruwe_datum}'.")
        geziene_datums.add(ruwe_datum)

        resultaten.append((ruwe_datum, omzet))

    return resultaten
