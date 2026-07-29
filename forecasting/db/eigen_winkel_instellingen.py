"""Gemiddelde omzet per verkocht stuk, per eigen winkel (zie
db/eigen_winkels.py) — vervangt het vroegere org-brede veld op
`organisaties`. `stel_prijs_in` doet een insert-of-update ("upsert" via
delete+insert binnen één transactie, consistent met hoe de rest van dit
project geen SQLite-specifieke ON CONFLICT-syntax gebruikt) omdat de rij
pas bestaat zodra een prijs voor het eerst gezet wordt."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import eigen_winkel_instellingen


def stel_prijs_in(engine: Engine, eigen_winkel_id: int, bedrag: float) -> None:
    with engine.begin() as conn:
        conn.execute(
            eigen_winkel_instellingen.delete().where(eigen_winkel_instellingen.c.eigen_winkel_id == eigen_winkel_id)
        )
        conn.execute(
            eigen_winkel_instellingen.insert().values(eigen_winkel_id=eigen_winkel_id, gemiddelde_omzet_per_stuk=bedrag)
        )


def haal_prijs(engine: Engine, eigen_winkel_id: int) -> Optional[float]:
    with engine.connect() as conn:
        return conn.execute(
            select(eigen_winkel_instellingen.c.gemiddelde_omzet_per_stuk).where(
                eigen_winkel_instellingen.c.eigen_winkel_id == eigen_winkel_id
            )
        ).scalar_one_or_none()
