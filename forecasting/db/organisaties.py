"""Organisatie-brede instellingen en levenscyclus (activeren/deactiveren/
verwijderen, Stripe-koppeling, proefperiode). De gemiddelde omzet per
verkocht stuk verhuisde naar db/eigen_winkel_instellingen.py — die is nu
per eigen winkel ingesteld, niet meer org-breed."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine

from db.schema import (
    aanmeldingen,
    api_keys,
    eigen_product_verkoopdata,
    eigen_verkoopdata,
    eigen_winkel_instellingen,
    eigen_winkels,
    gebruiker_winkels,
    gebruikers,
    organisaties,
    sessies,
    wachtwoord_reset_tokens,
    winkels,
)


def _als_utc(moment: datetime) -> datetime:
    """SQLite/SQLAlchemy geeft datetimes terug zonder tijdzone-info, ook al
    is er altijd UTC ingeschreven — zelfde reden/patroon als db.sessies.
    _als_utc en db.wachtwoord_reset._als_utc."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


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


def heractiveer_organisatie(engine: Engine, organisatie_id: int) -> None:
    """Er bestaat vandaag geen geautomatiseerd reactivatie-pad (zie de
    designspec) — dit is de functie die een operator's handmatige-reactivatie
    tooling MOET aanroepen (nooit een kale `actief=True`-update) als een
    wrongly-cancelled abonnement via directe SQL rechtgezet wordt. Zet
    gedeactiveerd_op expliciet terug naar None in dezelfde update als
    actief=True, zodat dat veld nooit stale kan blijven staan t.o.v. actief.
    Zonder dit zou een oude gedeactiveerd_op-tijdstempel overleven, en bij
    een latere, nieuwe deactivering (deactiveer_organisatie() zet 'm dan wel
    opnieuw, maar tussen de handmatige reactivatie en die volgende
    deactivering in kan haal_te_verwijderen_organisaties() nog steeds de
    oude waarde zien als iemand direct SQL gebruikt) de organisatie meteen,
    zonder enige nieuwe 30-dagen-wachtperiode, in aanmerking laten komen
    voor definitieve verwijdering — precies de bug die de finale review van
    deze branch blootlegde."""
    with engine.begin() as conn:
        conn.execute(
            organisaties.update().where(organisaties.c.id == organisatie_id)
            .values(actief=True, gedeactiveerd_op=None)
        )


def haal_te_verwijderen_organisaties(engine: Engine, nu: datetime, wachtdagen: int = 30) -> list[int]:
    """Voor db.opschonen_cli: welke organisaties zijn lang genoeg geleden
    gedeactiveerd om nu definitief verwijderd te mogen worden
    (verwijder_organisatie() hieronder). Los van die functie gehouden
    zodat de selectielogica (wíé komt in aanmerking) apart getest kan
    worden van de verwijdering zelf (wát er precies gebeurt als iemand
    verwijderd wordt)."""
    grens = nu - timedelta(days=wachtdagen)
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.id).where(
                organisaties.c.actief.is_(False),
                organisaties.c.gedeactiveerd_op.isnot(None),
                organisaties.c.gedeactiveerd_op < grens,
            )
        ).scalars().all()


def verwijder_organisatie(engine: Engine, organisatie_id: int) -> None:
    """Definitieve, onomkeerbare verwijdering (AVG-vereiste, beslissing 9
    in FASE4-SAAS-FOUNDATION.md) — aangeroepen door db.opschonen_cli, 30
    dagen na deactiveer_organisatie(). Eén transactie: alle betrokken
    tabellen worden leeggemaakt vóór de organisaties-rij zelf verdwijnt,
    zodat er nooit een tussentoestand met wees-rijen op schijf staat.
    aanmeldingen blijft als historisch aanmeld-record bestaan (het bevat
    op zichzelf geen persoonsgegevens meer zodra gebruikers/organisaties
    weg zijn), alleen de FK-verwijzing wordt losgekoppeld. De audit-log
    (security/audit.py) blijft bewust buiten dit bereik — zie de
    designspec voor de reden."""
    with engine.begin() as conn:
        gebruiker_ids = select(gebruikers.c.id).where(gebruikers.c.organisatie_id == organisatie_id)
        winkel_ids = select(winkels.c.id).where(winkels.c.organisatie_id == organisatie_id)
        eigen_winkel_ids = select(eigen_winkels.c.id).where(eigen_winkels.c.organisatie_id == organisatie_id)

        conn.execute(sessies.delete().where(sessies.c.gebruiker_id.in_(gebruiker_ids)))
        conn.execute(wachtwoord_reset_tokens.delete().where(wachtwoord_reset_tokens.c.gebruiker_id.in_(gebruiker_ids)))
        conn.execute(gebruiker_winkels.delete().where(gebruiker_winkels.c.winkel_id.in_(winkel_ids)))
        conn.execute(api_keys.delete().where(api_keys.c.organisatie_id == organisatie_id))
        conn.execute(eigen_verkoopdata.delete().where(eigen_verkoopdata.c.eigen_winkel_id.in_(eigen_winkel_ids)))
        conn.execute(
            eigen_product_verkoopdata.delete().where(eigen_product_verkoopdata.c.eigen_winkel_id.in_(eigen_winkel_ids))
        )
        conn.execute(
            eigen_winkel_instellingen.delete().where(eigen_winkel_instellingen.c.eigen_winkel_id.in_(eigen_winkel_ids))
        )
        conn.execute(eigen_winkels.delete().where(eigen_winkels.c.organisatie_id == organisatie_id))
        conn.execute(winkels.delete().where(winkels.c.organisatie_id == organisatie_id))
        conn.execute(gebruikers.delete().where(gebruikers.c.organisatie_id == organisatie_id))
        conn.execute(
            aanmeldingen.update().where(aanmeldingen.c.organisatie_id == organisatie_id).values(organisatie_id=None)
        )
        conn.execute(organisaties.delete().where(organisaties.c.id == organisatie_id))


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
