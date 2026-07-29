"""Fase 5 NODIG 3: wekelijkse proactieve herbestel-mail (maandagochtend,
zie serving/herbestel_email_cli.py voor de cron-invocatie). Twee bronnen
per organisatie, allebei in dezelfde mail als er iets te melden is:
1. Winkels in het gedeelde model (db.winkels.lijst_winkels) — dezelfde
   winkel_samenvatting()-berekening als het portfolio-dashboard, opgeteld
   over alle winkels van de organisatie. Herbestel-prijs: het org-brede
   db.organisaties.gemiddelde_omzet_per_stuk.
2. Elke eigen winkel (db.eigen_winkels) met genoeg geüploade
   verkoopdata (serving.eigen_voorspelling) krijgt een eigen sectie in
   dezelfde mail — nooit opgeteld tot één org-totaal, want verschillende
   eigen winkels kunnen andere producten/prijzen hebben. Herbestel-prijs
   per eigen winkel: automatisch afgeleid (serving.prijs_per_stuk) met
   het handmatig ingestelde bedrag (db.eigen_winkel_instellingen) als
   terugval.
Een organisatie zonder gedeeld-model-winkels én zonder eigen winkel met
genoeg historie heeft niets te melden en wordt overgeslagen, geen mail."""
from __future__ import annotations

import sys
from datetime import date
from typing import Optional

import pandas as pd

from db import eigen_winkel_instellingen as db_eigen_winkel_instellingen
from db import eigen_winkels as db_eigen_winkels
from db import gebruikers as db_gebruikers
from db import organisaties as db_organisaties
from db import product_verkoopdata as db_product_verkoopdata
from db import verkoopdata as db_verkoopdata
from db import winkels as db_winkels
from security import mail
from serving.eigen_voorspelling import bereken_eigen_voorspelling
from serving.forecast import herbestel_advies, winkel_samenvatting
from serving.prijs_per_stuk import bereken_gemiddelde_prijs_per_stuk

HORIZON_DAGEN = 7


def _verzamel_forecast_via_gedeeld_model(
    modellen, historie: pd.DataFrame, winkel_metadata: pd.DataFrame, winkels, start_datum: date
) -> Optional[dict]:
    if not winkels:
        return None
    totaal_p10 = totaal_p50 = totaal_p90 = 0.0
    minstens_een_winkel_gelukt = False
    for extern_store_id, _naam in winkels:
        # Bij een portfolio van honderden winkels (bv. het gedeelde
        # Rossmann-model) mist er vrijwel altijd wel één winkel genoeg
        # historie voor deze startdatum (net geopend, lange sluiting) —
        # dat mag de voorspelling voor de rest van de organisatie niet
        # blokkeren, net zomin als een mislukte mail dat mag (zie
        # verstuur_wekelijkse_herbestel_mails hieronder).
        try:
            samenvatting = winkel_samenvatting(
                modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
                store_id=extern_store_id, start_datum=pd.Timestamp(start_datum), horizon_dagen=HORIZON_DAGEN,
            )
        except Exception as e:
            print(f"Winkel {extern_store_id} overgeslagen in herbestel-mail: {e}", file=sys.stderr)
            continue
        totaal_p10 += samenvatting["totaal_p10"]
        totaal_p50 += samenvatting["totaal_p50"]
        totaal_p90 += samenvatting["totaal_p90"]
        minstens_een_winkel_gelukt = True
    if not minstens_een_winkel_gelukt:
        return None
    return {"totaal_p10": totaal_p10, "totaal_p50": totaal_p50, "totaal_p90": totaal_p90}


def _verzamel_secties_via_eigen_winkels(engine, organisatie_id: int, start_datum: date) -> list[dict]:
    secties = []
    for winkel in db_eigen_winkels.lijst_eigen_winkels(engine, organisatie_id=organisatie_id):
        rijen = db_verkoopdata.haal_verkoopdata(engine, eigen_winkel_id=winkel["id"])
        resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=HORIZON_DAGEN, vanaf=start_datum)
        if resultaat is None:
            continue
        product_rijen = db_product_verkoopdata.haal_product_verkoopdata(engine, eigen_winkel_id=winkel["id"])
        prijs = bereken_gemiddelde_prijs_per_stuk(rijen, product_rijen)
        if prijs is None:
            prijs = db_eigen_winkel_instellingen.haal_prijs(engine, eigen_winkel_id=winkel["id"])
        advies = herbestel_advies(resultaat["totaal_p10"], resultaat["totaal_p50"], resultaat["totaal_p90"], prijs)
        secties.append({
            "naam": winkel["naam"], "totaal_p10": resultaat["totaal_p10"],
            "totaal_p50": resultaat["totaal_p50"], "totaal_p90": resultaat["totaal_p90"], "advies": advies,
        })
    return secties


def bouw_email_inhoud(
    organisatie_naam: str, gedeeld_model_forecast: Optional[dict], eigen_winkel_secties: list[dict]
) -> tuple[str, str]:
    onderwerp = f"Wekelijkse voorspelling voor {organisatie_naam}"
    blokken = []
    if gedeeld_model_forecast:
        p10, p50, p90 = (gedeeld_model_forecast[k] for k in ("totaal_p10", "totaal_p50", "totaal_p90"))
        advies = gedeeld_model_forecast.get("advies")
        if advies:
            blokken.append(
                f"Bestel deze week ongeveer {advies['stuks_p50']} stuks bij. Houd rekening met pieken tot "
                f"{advies['stuks_p90']} stuks bij drukte, en met minder verkoop tot {advies['stuks_p10']} stuks "
                "als het rustiger is dan verwacht."
            )
        else:
            blokken.append(
                (f"Verwachte omzet komende {HORIZON_DAGEN} dagen: ongeveer €{p50:,.0f} "
                 f"(bandbreedte €{p10:,.0f} tot €{p90:,.0f}).").replace(",", ".")
            )
    for sectie in eigen_winkel_secties:
        p10, p50, p90 = sectie["totaal_p10"], sectie["totaal_p50"], sectie["totaal_p90"]
        kop = f"{sectie['naam']}:"
        if sectie["advies"]:
            regel = (
                f"Bestel deze week ongeveer {sectie['advies']['stuks_p50']} stuks bij. Houd rekening met pieken "
                f"tot {sectie['advies']['stuks_p90']} stuks bij drukte, en met minder verkoop tot "
                f"{sectie['advies']['stuks_p10']} stuks als het rustiger is dan verwacht."
            )
        else:
            regel = (
                f"Verwachte omzet komende {HORIZON_DAGEN} dagen: ongeveer €{p50:,.0f} "
                f"(bandbreedte €{p10:,.0f} tot €{p90:,.0f})."
            ).replace(",", ".")
        blokken.append(f"{kop}\n{regel}")
    tekst = (
        f"Hallo,\n\nDit is je wekelijkse update van KwantIQ voor {organisatie_naam}.\n\n"
        + "\n\n".join(blokken) + "\n\nLog in op je dashboard voor de details.\n"
    )
    return onderwerp, tekst


def verstuur_wekelijkse_herbestel_mails(
    engine, modellen, historie: pd.DataFrame, winkel_metadata: pd.DataFrame, mail_config: dict, start_datum: date,
) -> list[str]:
    """Loopt elke actieve organisatie langs, verzamelt zowel het gedeeld-
    model-forecast (indien winkels aanwezig) als een sectie per eigen
    winkel met genoeg historie, en verstuurt één mail naar de eigenaar als
    er iets te melden is. Geeft de e-mailadressen terug waar echt naar
    verstuurd is. Een mislukte mail voor één organisatie (bv. een
    tijdelijke SMTP-storing) mag de rest van de batch nooit blokkeren —
    best-effort per organisatie, met een regel naar stderr zodat een
    mislukking wel zichtbaar blijft in de cron-log."""
    verstuurd = []
    for org in db_organisaties.lijst_actieve_organisaties(engine):
        winkels = db_winkels.lijst_winkels(engine, organisatie_id=org.id)
        gedeeld_model_forecast = _verzamel_forecast_via_gedeeld_model(
            modellen, historie, winkel_metadata, winkels, start_datum
        )
        eigen_winkel_secties = _verzamel_secties_via_eigen_winkels(engine, org.id, start_datum)
        if gedeeld_model_forecast is None and not eigen_winkel_secties:
            continue

        eigenaar_email = db_gebruikers.haal_eigenaar_email(engine, organisatie_id=org.id)
        if eigenaar_email is None:
            continue

        if gedeeld_model_forecast:
            prijs = db_organisaties.haal_gemiddelde_omzet_per_stuk(engine, organisatie_id=org.id)
            gedeeld_model_forecast["advies"] = herbestel_advies(
                gedeeld_model_forecast["totaal_p10"], gedeeld_model_forecast["totaal_p50"],
                gedeeld_model_forecast["totaal_p90"], prijs,
            )

        onderwerp, tekst = bouw_email_inhoud(org.naam, gedeeld_model_forecast, eigen_winkel_secties)

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
