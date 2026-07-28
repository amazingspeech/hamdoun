"""Fase 5 NODIG 2 (afgeslankt): opslag voor handmatig geüploade eigen
verkoopdata (zie serving/verkoopdata.py voor de CSV-parser)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import eigen_verkoopdata


def vervang_verkoopdata(engine: Engine, organisatie_id: int, rijen: list[tuple[str, float]]) -> None:
    """Vervangt de volledige verkoopdata van een organisatie door precies
    de opgegeven rijen — een nieuwe upload vervangt de vorige set in
    plaats van ermee samen te voegen, zodat een winkelier niet zelf hoeft
    uit te zoeken welke datums al bestonden."""
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(eigen_verkoopdata.delete().where(eigen_verkoopdata.c.organisatie_id == organisatie_id))
        if not rijen:
            return
        conn.execute(
            eigen_verkoopdata.insert(),
            [{"organisatie_id": organisatie_id, "datum": datum, "omzet": omzet, "aangemaakt_op": nu}
             for datum, omzet in rijen],
        )


def haal_verkoopdata(engine: Engine, organisatie_id: int) -> list[dict]:
    with engine.connect() as conn:
        rijen = conn.execute(
            select(eigen_verkoopdata.c.datum, eigen_verkoopdata.c.omzet)
            .where(eigen_verkoopdata.c.organisatie_id == organisatie_id)
            .order_by(eigen_verkoopdata.c.datum)
        ).all()
    return [{"datum": r.datum, "omzet": r.omzet} for r in rijen]
