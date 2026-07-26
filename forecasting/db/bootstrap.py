"""Eenmalige bootstrap voor Stap 0 (Fase 4): één organisatie aanmaken en
alle bestaande store-ID's uit het actieve modelartefact daaraan koppelen.
Geen gedragsverandering aan de API — deze functie wordt losstaand
aangeroepen (zie db/cli.py), niet vanuit serving/app.py."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.engine import Engine

from db.schema import organisaties, winkels


def bootstrap_organisatie(engine: Engine, naam: str, slug: str, store_ids: list[int]) -> int:
    """Maakt één organisatie aan en koppelt elke store_id uit store_ids
    eraan als winkel. Geeft het id van de aangemaakte organisatie terug.
    Faalt hard (IntegrityError) bij een dubbele slug of een store_id die al
    aan een andere organisatie hangt — nooit stilzwijgend overschrijven."""
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        org_id = conn.execute(
            organisaties.insert().values(naam=naam, slug=slug, actief=True, aangemaakt_op=nu)
        ).inserted_primary_key[0]

        if store_ids:
            conn.execute(
                winkels.insert(),
                [
                    {
                        "organisatie_id": org_id,
                        "extern_store_id": store_id,
                        "naam": None,
                        "actief": True,
                        "aangemaakt_op": nu,
                    }
                    for store_id in store_ids
                ],
            )

    return org_id
