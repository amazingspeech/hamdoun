"""Fase 5 NODIG 3: wekelijkse proactieve herbestel-mail (maandagochtend,
zie serving/herbestel_email_cli.py voor de cron-invocatie). Twee bronnen
per organisatie, in deze volgorde:
1. Winkels in het gedeelde model (db.winkels.lijst_winkels) — dezelfde
   winkel_samenvatting()-berekening als het portfolio-dashboard, opgeteld
   over alle winkels van de organisatie.
2. Geen winkels in het gedeelde model? Dan de eigen geüploade verkoopdata
   (serving.eigen_voorspelling) — de enige route voor elke self-serve
   organisatie, die per ontwerp nooit een winkel in het gedeelde,
   Rossmann-getrainde model heeft (zie serving/forecast.py: OnbekendeWinkel
   — er is geen manier om een nieuwe zaak alsnog in dat model te krijgen).
Een organisatie zonder winkels én zonder genoeg eigen verkoopdata heeft
niets te melden en wordt overgeslagen, geen mail."""
from __future__ import annotations

import sys
from datetime import date
from typing import Optional

import pandas as pd

from db import gebruikers as db_gebruikers
from db import organisaties as db_organisaties
from db import verkoopdata as db_verkoopdata
from db import winkels as db_winkels
from security import mail
from serving.eigen_voorspelling import bereken_eigen_voorspelling
from serving.forecast import herbestel_advies, winkel_samenvatting

HORIZON_DAGEN = 7


def _verzamel_forecast_via_gedeeld_model(
    modellen, historie: pd.DataFrame, winkel_metadata: pd.DataFrame, winkels, start_datum: date
) -> Optional[dict]:
    if not winkels:
        return None
    totaal_p10 = totaal_p50 = totaal_p90 = 0.0
    for extern_store_id, _naam in winkels:
        samenvatting = winkel_samenvatting(
            modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
            store_id=extern_store_id, start_datum=pd.Timestamp(start_datum), horizon_dagen=HORIZON_DAGEN,
        )
        totaal_p10 += samenvatting["totaal_p10"]
        totaal_p50 += samenvatting["totaal_p50"]
        totaal_p90 += samenvatting["totaal_p90"]
    return {"totaal_p10": totaal_p10, "totaal_p50": totaal_p50, "totaal_p90": totaal_p90}


def _verzamel_forecast_via_eigen_data(engine, organisatie_id: int, start_datum: date) -> Optional[dict]:
    rijen = db_verkoopdata.haal_verkoopdata(engine, organisatie_id=organisatie_id)
    resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=HORIZON_DAGEN, vanaf=start_datum)
    if resultaat is None:
        return None
    return {
        "totaal_p10": resultaat["totaal_p10"], "totaal_p50": resultaat["totaal_p50"],
        "totaal_p90": resultaat["totaal_p90"],
    }


def bouw_email_inhoud(
    organisatie_naam: str, totaal_p10: float, totaal_p50: float, totaal_p90: float, advies: Optional[dict]
) -> tuple[str, str]:
    onderwerp = f"Wekelijkse voorspelling voor {organisatie_naam}"
    omzet_alinea = (
        f"Verwachte omzet komende {HORIZON_DAGEN} dagen: ongeveer €{totaal_p50:,.0f} "
        f"(bandbreedte €{totaal_p10:,.0f} tot €{totaal_p90:,.0f})."
    ).replace(",", ".")
    if advies:
        kern_alinea = (
            f"Bestel deze week ongeveer {advies['stuks_p50']} stuks bij. Houd rekening met pieken tot "
            f"{advies['stuks_p90']} stuks bij drukte, en met minder verkoop tot {advies['stuks_p10']} stuks "
            "als het rustiger is dan verwacht."
        )
    else:
        kern_alinea = omzet_alinea
    tekst = (
        f"Hallo,\n\nDit is je wekelijkse update van Vraagvoorspelling voor {organisatie_naam}.\n\n"
        f"{omzet_alinea}\n\n{kern_alinea}\n\nLog in op je dashboard voor de details.\n"
    )
    return onderwerp, tekst


def verstuur_wekelijkse_herbestel_mails(
    engine, modellen, historie: pd.DataFrame, winkel_metadata: pd.DataFrame, mail_config: dict, start_datum: date,
) -> list[str]:
    """Loopt elke actieve organisatie langs, berekent een forecast (eerst
    via het gedeelde model, anders via eigen verkoopdata), en verstuurt een
    mail naar de eigenaar als er iets te melden is. Geeft de e-mailadressen
    terug waar echt naar verstuurd is. Een mislukte mail voor één
    organisatie (bv. een tijdelijke SMTP-storing) mag de rest van de batch
    nooit blokkeren — best-effort per organisatie, met een regel naar
    stderr zodat een mislukking wel zichtbaar blijft in de cron-log."""
    verstuurd = []
    for org in db_organisaties.lijst_actieve_organisaties(engine):
        winkels = db_winkels.lijst_winkels(engine, organisatie_id=org.id)
        forecast = _verzamel_forecast_via_gedeeld_model(modellen, historie, winkel_metadata, winkels, start_datum)
        if forecast is None:
            forecast = _verzamel_forecast_via_eigen_data(engine, org.id, start_datum)
        if forecast is None:
            continue

        eigenaar_email = db_gebruikers.haal_eigenaar_email(engine, organisatie_id=org.id)
        if eigenaar_email is None:
            continue

        prijs = db_organisaties.haal_gemiddelde_omzet_per_stuk(engine, organisatie_id=org.id)
        advies = herbestel_advies(forecast["totaal_p10"], forecast["totaal_p50"], forecast["totaal_p90"], prijs)
        onderwerp, tekst = bouw_email_inhoud(
            org.naam, forecast["totaal_p10"], forecast["totaal_p50"], forecast["totaal_p90"], advies
        )

        try:
            mail.verstuur(
                smtp_host=mail_config.get("smtp_host"), smtp_poort=mail_config.get("smtp_poort"),
                afzender=mail_config.get("afzender"), smtp_gebruiker=mail_config.get("smtp_gebruiker"),
                smtp_wachtwoord=mail_config.get("smtp_wachtwoord"),
                ontvanger=eigenaar_email, onderwerp=onderwerp, tekst=tekst,
            )
            verstuurd.append(eigenaar_email)
        except Exception as e:
            print(f"Herbestel-mail voor organisatie {org.naam!r} (id={org.id}) mislukt: {e}", file=sys.stderr)

    return verstuurd
