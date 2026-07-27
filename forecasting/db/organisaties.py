"""Fase 5 NODIG 1 (herbestel-advies): per-organisatie instellingen die niet
uit het modelartefact of een koppeling komen, maar door de winkelier zelf
worden opgegeven — momenteel alleen de gemiddelde omzet per verkocht stuk,
nodig om een omzetvoorspelling om te rekenen naar een stuks-schatting."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import organisaties


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
