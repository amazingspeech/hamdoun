"""Fase 4 Stap 2: de daadwerkelijke isolatie-check. Antwoordt op precies
één vraag — hoort dit store_id bij deze organisatie? — en verder niets.
serving/app.py gebruikt dit vóór elke /forecast-aanroep; een 'nee' hier
wordt door de aanroeper als 404 behandeld (nooit 403, zie
FASE4-SAAS-FOUNDATION.md: een 403 zou bevestigen dat het store_id bestaat
maar van een ander is, wat store-ID's van andere organisaties
enumereerbaar maakt)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import winkels


def hoort_store_bij_organisatie(engine: Engine, store_id: int, organisatie_id: int) -> bool:
    with engine.connect() as conn:
        rij = conn.execute(
            select(winkels.c.id).where(
                winkels.c.extern_store_id == store_id,
                winkels.c.organisatie_id == organisatie_id,
            )
        ).first()
    return rij is not None
