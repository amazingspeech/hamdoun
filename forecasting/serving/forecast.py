"""Voorspellingslogica: reconstrueert features uit de gebundelde historie en
roept de drie kwantielmodellen aan.

Voorspelt recursief: elke volgende dag gebruikt de p50-voorspelling van
eerder voorspelde dagen als werkwaarde voor de lag-/rolling-features. Dit is
nodig omdat de gevalideerde horizon (tot 48 dagen) de langste lag (21 dagen)
kan overschrijden — de werkelijke omzet van een nog niet aangebroken dag is
per definitie onbekend. Compounding van fouten over een langere horizon is
een bekende, geaccepteerde beperking van deze aanpak (zie
KNOWN-LIMITATIONS.md). Hergebruikt dezelfde featurefuncties als tijdens
training, zodat serving-tijd-features nooit op een subtiel andere manier
worden berekend dan trainings-tijd-features."""
from __future__ import annotations

from datetime import date, timedelta
from typing import NamedTuple

import numpy as np
import pandas as pd
import shap

from pipeline.features import voeg_kalenderfeatures_toe, voeg_lag_features_toe
from training.evaluate import sorteer_kwantielen
from training.train import FEATURE_KOLOMMEN

# Groepeert de 14 losse featurekolommen tot betekenisvolle, uitlegbare
# categorieën voor een winkelier — niemand heeft iets aan "omzet_lag_14"
# als los begrip. Store en CompetitionDistance staan er bewust niet in:
# die zijn constant binnen één winkel/aanvraag, verklaren dus nooit
# waarom DEZE periode afwijkt, alleen waarom deze winkel in het algemeen
# van een gemiddelde winkel verschilt — een andere vraag dan waar dit
# uitlegblok antwoord op geeft.
_FACTOR_BUCKETS = {
    "Promotie": ["Promo"],
    "Schoolvakantie": ["SchoolHoliday"],
    "Seizoen": ["DayOfWeek", "Jaar", "Maand", "Dag", "Weeknummer"],
    "Recente verkooptrend": [
        "omzet_lag_7", "omzet_lag_14", "omzet_lag_21",
        "omzet_rolling_gemiddeld_7", "omzet_rolling_gemiddeld_28",
    ],
}


class OnbekendeWinkel(Exception):
    pass


class HorizonBuitenBereik(Exception):
    pass


class VoorspelResultaat(NamedTuple):
    voorspellingen: pd.DataFrame
    belangrijkste_factoren: list[dict]


def belangrijkste_factoren(model: object, feature_rijen: pd.DataFrame, top_n: int = 2) -> list[dict]:
    """Aggregeert SHAP-bijdrages van het p50-model per featuregroep over
    alle voorspelde dagen samen (één uitleg voor de hele periode, geen
    losse uitleg per dag — sluit aan bij hoe de rest van het dashboard al
    op periodeniveau samenvat). Geeft de top_n grootste bijdrages terug,
    gesorteerd op absolute grootte; een bijdrage van precies 0 wordt
    overgeslagen (niets om over te zeggen)."""
    verklaarder = shap.TreeExplainer(model)
    shap_waarden = verklaarder.shap_values(feature_rijen[FEATURE_KOLOMMEN])
    shap_df = pd.DataFrame(shap_waarden, columns=FEATURE_KOLOMMEN)

    bijdrages = {naam: float(shap_df[kolommen].to_numpy().sum()) for naam, kolommen in _FACTOR_BUCKETS.items()}
    gesorteerd = sorted(bijdrages.items(), key=lambda item: abs(item[1]), reverse=True)
    return [
        {"naam": naam, "richting": "hoger" if waarde > 0 else "lager"}
        for naam, waarde in gesorteerd[:top_n] if waarde != 0
    ]


def dagreeks(van: date | None, tot: date | None) -> set[date]:
    """Zet een optionele van/tot-periode om in de losse dagen erin
    (inclusief beide uiteinden). Geeft een lege set als van ontbreekt; als
    tot ontbreekt wordt het als één dag (van) behandeld — vergevingsgezind
    voor een enkele promotiedag zonder dat de aanroeper expliciet tot
    hoeft mee te geven."""
    if van is None:
        return set()
    eind = tot or van
    if eind < van:
        van, eind = eind, van
    return {van + timedelta(days=i) for i in range((eind - van).days + 1)}


def winkel_samenvatting(
    modellen: dict[float, object],
    historie: pd.DataFrame,
    winkel_metadata: pd.DataFrame,
    store_id: int,
    start_datum: pd.Timestamp,
    horizon_dagen: int,
    afwijking_drempel: float = 0.25,
) -> dict:
    """Eén winkel samengevat voor het portfolio-overzicht: totaal
    p10/p50/p90, een sparkline (dagelijkse p50-reeks) en een 'afwijkend'-
    vlag. Afwijkend betekent hier: het voorspelde daggemiddelde wijkt meer
    dan afwijking_drempel (standaard 25%) af van het daggemiddelde over de
    laatste horizon_dagen werkelijke (open) dagen van diezelfde winkel —
    vergeleken met de eigen historie, niet met andere winkels, want elke
    winkel heeft een ander normaal niveau."""
    resultaat = voorspel_periode(
        modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        store_id=store_id, start_datum=start_datum, horizon_dagen=horizon_dagen,
    )
    v = resultaat.voorspellingen
    totaal_p50 = float(v["p50"].sum())

    eigen_historie = historie[(historie["Store"] == store_id) & (historie["Open"] == 1)].sort_values("Date")
    recent = eigen_historie.tail(horizon_dagen)
    afwijkend = False
    if not recent.empty:
        historisch_gemiddeld = float(recent["Sales"].mean())
        voorspeld_gemiddeld = totaal_p50 / horizon_dagen
        if historisch_gemiddeld > 0:
            afwijkend = abs(voorspeld_gemiddeld - historisch_gemiddeld) / historisch_gemiddeld > afwijking_drempel

    return {
        "totaal_p50": totaal_p50,
        "totaal_p10": float(v["p10"].sum()),
        "totaal_p90": float(v["p90"].sum()),
        "sparkline": [float(x) for x in v["p50"].tolist()],
        "afwijkend": afwijkend,
    }


def vorige_periode_omzet(
    historie: pd.DataFrame,
    store_id: int,
    start_datum: pd.Timestamp,
    horizon_dagen: int,
) -> float | None:
    """Som van de werkelijke omzet over de horizon_dagen open dagen die
    onmiddellijk voorafgaan aan start_datum — voor de periodevergelijking
    naast de voorspelling. Geeft None als er niet minstens horizon_dagen
    voorafgaande open dagen bekend zijn, zodat een gedeeltelijk venster
    nooit stilzwijgend als volledige periode wordt vergeleken."""
    start_datum = pd.Timestamp(start_datum)
    eigen_historie = historie[
        (historie["Store"] == store_id) & (historie["Open"] == 1) & (historie["Date"] < start_datum)
    ].sort_values("Date")
    recent = eigen_historie.tail(horizon_dagen)
    if len(recent) < horizon_dagen:
        return None
    return float(recent["Sales"].sum())


def voorspel_periode(
    modellen: dict[float, object],
    historie: pd.DataFrame,
    winkel_metadata: pd.DataFrame,
    store_id: int,
    start_datum: pd.Timestamp,
    horizon_dagen: int,
    promo_datums: set[date] | None = None,
    schoolvakantie_datums: set[date] | None = None,
    verklaar: bool = False,
) -> VoorspelResultaat:
    promo_datums = promo_datums or set()
    schoolvakantie_datums = schoolvakantie_datums or set()
    if store_id not in historie["Store"].unique():
        raise OnbekendeWinkel(f"Onbekend store_id: {store_id}")

    start_datum = pd.Timestamp(start_datum)
    # Preserve all input columns from history, filtering to the requested store
    store_history = historie[historie["Store"] == store_id].copy()
    # Ensure we have the essential columns; if missing from input, they'll be NaN and raise HorizonBuitenBereik
    essential_cols = ["Store", "Date", "Sales", "Open"]
    werkreeks = store_history[essential_cols].copy()
    # Preserve DayOfWeek, Promo, SchoolHoliday if they exist in the input
    for col in ["DayOfWeek", "Promo", "SchoolHoliday"]:
        if col in store_history.columns:
            werkreeks[col] = store_history[col].values
    resultaten = []
    alle_feature_rijen = []

    for i in range(horizon_dagen):
        doel_datum = start_datum + pd.Timedelta(days=i)
        nieuwe_rij = pd.DataFrame({
            "Store": [store_id], "Date": [doel_datum], "Sales": [np.nan], "Open": [1],
            "DayOfWeek": [doel_datum.dayofweek + 1],
            # Standaard 0 (geen promo/vakantie) tenzij de aanroeper die dag
            # expliciet opgeeft — vóór deze parameters bestond er geen
            # manier om dit ooit anders te zetten, wat een structurele
            # onderschatting gaf op precies de dagen die winkeliers plannen.
            "Promo": [1 if doel_datum.date() in promo_datums else 0],
            "SchoolHoliday": [1 if doel_datum.date() in schoolvakantie_datums else 0],
        })
        volledig = pd.concat([werkreeks, nieuwe_rij], ignore_index=True)
        volledig = voeg_kalenderfeatures_toe(volledig)
        volledig = voeg_lag_features_toe(volledig)
        volledig = volledig.merge(winkel_metadata, on="Store", how="left")

        feature_rij = volledig.iloc[[-1]]
        if feature_rij[FEATURE_KOLOMMEN].isna().any(axis=1).iloc[0]:
            raise HorizonBuitenBereik(
                f"Onvoldoende historie om {doel_datum.date()} te voorspellen voor winkel {store_id}."
            )

        alle_feature_rijen.append(feature_rij)
        ruwe = {q: float(modellen[q].predict(feature_rij[FEATURE_KOLOMMEN])[0]) for q in (0.1, 0.5, 0.9)}
        p10, p50, p90 = sorteer_kwantielen(
            np.array([ruwe[0.1]]), np.array([ruwe[0.5]]), np.array([ruwe[0.9]])
        )
        resultaten.append({"Date": doel_datum, "p10": float(p10[0]), "p50": float(p50[0]), "p90": float(p90[0])})

        werkreeks = pd.concat(
            [werkreeks, pd.DataFrame({"Store": [store_id], "Date": [doel_datum], "Sales": [float(p50[0])], "Open": [1]})],
            ignore_index=True,
        )

    factoren = []
    if verklaar:
        factoren = belangrijkste_factoren(modellen[0.5], pd.concat(alle_feature_rijen, ignore_index=True))

    return VoorspelResultaat(voorspellingen=pd.DataFrame(resultaten), belangrijkste_factoren=factoren)
