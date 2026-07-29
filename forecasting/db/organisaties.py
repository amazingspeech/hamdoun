"""Fase 5 NODIG 1 (herbestel-advies): per-organisatie instellingen die niet
uit het modelartefact of een koppeling komen, maar door de winkelier zelf
worden opgegeven — momenteel alleen de gemiddelde omzet per verkocht stuk,
nodig om een omzetvoorspelling om te rekenen naar een stuks-schatting."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine

from db.schema import organisaties


def _als_utc(moment: datetime) -> datetime:
    """SQLite/SQLAlchemy geeft datetimes terug zonder tijdzone-info, ook al
    is er altijd UTC ingeschreven — zelfde reden/patroon als db.sessies.
    _als_utc en db.wachtwoord_reset._als_utc."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def stel_gemiddelde_omzet_per_stuk_in(engine: Engine, organisatie_id: int, bedrag: float) -> None:
    with engine.begin() as conn:
        conn.execute(
            organisaties.update()
            .where(organisaties.c.id == organisatie_id)
            .values(gemiddelde_omzet_per_stuk=bedrag)
        )


def haal_gemiddelde_omzet_per_stuk(engine: Engine, organisatie_id: int) -> Optional[float]:
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.gemiddelde_omzet_per_stuk).where(organisaties.c.id == organisatie_id)
        ).scalar_one_or_none()


def _stel_stripe_koppeling_in_op_connectie(
    conn: Connection, organisatie_id: int, stripe_customer_id: str, stripe_subscription_id: str
) -> None:
    conn.execute(
        organisaties.update()
        .where(organisaties.c.id == organisatie_id)
        .values(stripe_customer_id=stripe_customer_id, stripe_subscription_id=stripe_subscription_id)
    )


def is_actief(engine: Engine, organisatie_id: int) -> bool:
    """Voor toegangscontrole (serving/app.py: login, vereis_sessie,
    vereis_toegang) — een onbekend organisatie_id levert bewust False op
    i.p.v. te crashen, zodat de aanroeper dit hetzelfde kan behandelen als
    een gedeactiveerde organisatie."""
    with engine.connect() as conn:
        waarde = conn.execute(
            select(organisaties.c.actief).where(organisaties.c.id == organisatie_id)
        ).scalar_one_or_none()
    return bool(waarde)


def haal_trial_verloopt_op(engine: Engine, organisatie_id: int) -> Optional[datetime]:
    """Voor de zijbalk (dashboard/account.js): hoeveel dagen resteren er
    nog in de proefperiode. None voor een organisatie die nooit in een
    proefperiode zit (handmatig aangemaakt) of waarvan de proefperiode al
    verstreken is — het aanroepende /me-endpoint toont dan geen
    aftellende dagen, alleen "alle functies actief"."""
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.trial_verloopt_op).where(organisaties.c.id == organisatie_id)
        ).scalar_one_or_none()


def is_in_proefperiode(engine: Engine, organisatie_id: int) -> bool:
    """True als deze organisatie nog binnen haar gratis proefperiode valt —
    gebruikt om premium-functies af te schermen (self-serve API-keys,
    promotie/schoolvakantie-invoer) zonder bij elk verzoek Stripe te
    bevragen. trial_verloopt_op is NULL voor handmatig aangemaakte
    organisaties (db.bootstrap.bootstrap_organisatie) — die zijn dus nooit
    in een proefperiode, ongeacht hoe lang geleden ze zijn aangemaakt."""
    with engine.connect() as conn:
        waarde = conn.execute(
            select(organisaties.c.trial_verloopt_op).where(organisaties.c.id == organisatie_id)
        ).scalar_one_or_none()
    if waarde is None:
        return False
    return _als_utc(waarde) > datetime.now(timezone.utc)


def deactiveer_organisatie(engine: Engine, organisatie_id: int) -> None:
    """Gezet door de webhook-handler zodra Stripe customer.subscription.
    deleted meldt (opzegging of einde van de betaalretry-cyclus) — zie
    serving/app.py. Zet ook gedeactiveerd_op, zodat db.opschonen_cli 30
    dagen later weet welke organisaties definitief verwijderd mogen
    worden (verwijder_organisatie() hieronder) — de daadwerkelijke
    verwijdering gebeurt hier nog niet: een geannuleerd abonnement kan
    nog binnen Stripe's eigen betaalretry-cyclus alsnog herstellen, en
    onomkeerbaar verwijderen op basis van één webhook-event zou daar geen
    ruimte voor geven."""
    with engine.begin() as conn:
        conn.execute(
            organisaties.update().where(organisaties.c.id == organisatie_id)
            .values(actief=False, gedeactiveerd_op=datetime.now(timezone.utc))
        )


def haal_organisatie_id_bij_stripe_subscription(engine: Engine, stripe_subscription_id: str) -> Optional[int]:
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.id).where(organisaties.c.stripe_subscription_id == stripe_subscription_id)
        ).scalar_one_or_none()


def lijst_actieve_organisaties(engine: Engine):
    """Voor de wekelijkse herbestel-mail (Fase 5 NODIG 3), die elke actieve
    organisatie langsloopt om te bepalen of er iets te melden valt."""
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.id, organisaties.c.naam).where(organisaties.c.actief.is_(True))
        ).all()


def stel_stripe_koppeling_in(
    engine: Engine, organisatie_id: int, stripe_customer_id: str, stripe_subscription_id: str,
    conn: Optional[Connection] = None,
) -> None:
    """Fase 5 NODIG 5: gezet door de webhook-handler (serving/app.py) zodra
    een self-serve aanmelding voltooid is — nodig als referentie voor
    toekomstig gebruik (opzeggen, factuurgeschiedenis tonen), niet voor
    toegangscontrole zelf (die blijft puur op organisatie_id lopen).

    conn: optioneel een al-openstaande connectie/transactie, zie
    db.bootstrap.bootstrap_organisatie voor dezelfde reden/patroon."""
    if conn is not None:
        _stel_stripe_koppeling_in_op_connectie(conn, organisatie_id, stripe_customer_id, stripe_subscription_id)
        return
    with engine.begin() as eigen_conn:
        _stel_stripe_koppeling_in_op_connectie(eigen_conn, organisatie_id, stripe_customer_id, stripe_subscription_id)


def kvk_nummer_heeft_organisatie(engine: Engine, kvk_nummer: str) -> bool:
    with engine.connect() as conn:
        rij = conn.execute(select(organisaties.c.id).where(organisaties.c.kvk_nummer == kvk_nummer)).first()
    return rij is not None


def haal_ingekochte_leden(engine: Engine, organisatie_id: int) -> Optional[int]:
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.ingekochte_leden).where(organisaties.c.id == organisatie_id)
        ).scalar_one_or_none()


def haal_ingekochte_winkels(engine: Engine, organisatie_id: int) -> Optional[int]:
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.ingekochte_winkels).where(organisaties.c.id == organisatie_id)
        ).scalar_one_or_none()
