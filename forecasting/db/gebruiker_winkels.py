"""Portfolio-dashboard item 10: welke winkels mag een gebruiker met
rol="lid" zien? Alleen relevant voor die rol — een eigenaar heeft altijd
org-brede toegang en wordt hier nooit voor geraadpleegd (zie
serving/app.py, waar de check alleen loopt als key.rol == "lid").
API-keys blijven org-breed werken zoals voorheen; deze laag geldt puur
voor sessie-gebaseerde (dashboard-)toegang, waar een specifieke
ingelogde gebruiker bekend is."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import gebruiker_winkels, gebruikers, winkels


def stel_toewijzingen_in(engine: Engine, gebruiker_id: int, extern_store_ids: list[int]) -> None:
    """Vervangt de volledige toewijzing van gebruiker_id door precies de
    opgegeven winkels — geen optelling met een vorige aanroep. Een lege
    lijst verwijdert alle toewijzingen. Draait in één transactie zodat een
    lezer nooit een tussentijds leeg-of-half-bijgewerkte set ziet."""
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(gebruiker_winkels.delete().where(gebruiker_winkels.c.gebruiker_id == gebruiker_id))
        if not extern_store_ids:
            return
        winkel_ids = conn.execute(
            select(winkels.c.id).where(winkels.c.extern_store_id.in_(extern_store_ids))
        ).scalars().all()
        conn.execute(
            gebruiker_winkels.insert(),
            [{"gebruiker_id": gebruiker_id, "winkel_id": winkel_id, "aangemaakt_op": nu} for winkel_id in winkel_ids],
        )


def lijst_toegewezen_winkels(engine: Engine, gebruiker_id: int) -> list[int]:
    """Geeft de extern_store_id's terug die aan gebruiker_id zijn
    toegewezen."""
    with engine.connect() as conn:
        return conn.execute(
            select(winkels.c.extern_store_id)
            .join(gebruiker_winkels, gebruiker_winkels.c.winkel_id == winkels.c.id)
            .where(gebruiker_winkels.c.gebruiker_id == gebruiker_id)
        ).scalars().all()


def migreer_bestaande_leden(engine: Engine) -> int:
    """Eenmalige migratie bij invoering van dit systeem: elk bestaand lid
    krijgt een toewijzing voor alle winkels die nu al bij hun organisatie
    horen, zodat niemand op het moment van deploy toegang verliest die ze
    al hadden. Slaat een lid dat al minstens één toewijzing heeft over —
    dit is een eenmalige bootstrap voor de overgang, geen doorlopende
    synchronisatie die een bewust ingeperkte toewijzing weer zou
    terugzetten naar 'alles'. Geeft het aantal daadwerkelijk gemigreerde
    leden terug."""
    with engine.connect() as conn:
        leden = conn.execute(
            select(gebruikers.c.id, gebruikers.c.organisatie_id).where(gebruikers.c.rol == "lid")
        ).all()

    aantal = 0
    for lid in leden:
        if lijst_toegewezen_winkels(engine, gebruiker_id=lid.id):
            continue
        with engine.connect() as conn:
            store_ids = conn.execute(
                select(winkels.c.extern_store_id).where(winkels.c.organisatie_id == lid.organisatie_id)
            ).scalars().all()
        if not store_ids:
            continue
        stel_toewijzingen_in(engine, gebruiker_id=lid.id, extern_store_ids=store_ids)
        aantal += 1
    return aantal


def hoort_winkel_bij_toewijzing(engine: Engine, gebruiker_id: int, extern_store_id: int) -> bool:
    with engine.connect() as conn:
        rij = conn.execute(
            select(gebruiker_winkels.c.id)
            .join(winkels, winkels.c.id == gebruiker_winkels.c.winkel_id)
            .where(
                gebruiker_winkels.c.gebruiker_id == gebruiker_id,
                winkels.c.extern_store_id == extern_store_id,
            )
        ).first()
    return rij is not None
