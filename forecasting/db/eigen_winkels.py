"""Eigen winkels: een naam-baar concept los van het ML-model-gekoppelde
`winkels`, puur om zelf geüploade verkoopdata onder te groeperen — zie
docs/superpowers/specs/2026-07-29-eigen-winkels-design.md."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import eigen_product_verkoopdata, eigen_verkoopdata, eigen_winkel_instellingen, eigen_winkels


def maak_eigen_winkel(engine: Engine, organisatie_id: int, naam: str) -> int:
    with engine.begin() as conn:
        return conn.execute(
            eigen_winkels.insert().values(
                organisatie_id=organisatie_id, naam=naam, aangemaakt_op=datetime.now(timezone.utc)
            )
        ).inserted_primary_key[0]


def lijst_eigen_winkels(engine: Engine, organisatie_id: int) -> list[dict]:
    with engine.connect() as conn:
        winkels = conn.execute(
            select(eigen_winkels.c.id, eigen_winkels.c.naam)
            .where(eigen_winkels.c.organisatie_id == organisatie_id)
            .order_by(eigen_winkels.c.naam)
        ).all()
        resultaat = []
        for winkel in winkels:
            heeft_verkoopdata = conn.execute(
                select(eigen_verkoopdata.c.id).where(eigen_verkoopdata.c.eigen_winkel_id == winkel.id)
            ).first() is not None
            resultaat.append({"id": winkel.id, "naam": winkel.naam, "heeft_verkoopdata": heeft_verkoopdata})
    return resultaat


def hernoem_eigen_winkel(engine: Engine, organisatie_id: int, eigen_winkel_id: int, nieuwe_naam: str) -> bool:
    with engine.begin() as conn:
        resultaat = conn.execute(
            eigen_winkels.update()
            .where(eigen_winkels.c.id == eigen_winkel_id, eigen_winkels.c.organisatie_id == organisatie_id)
            .values(naam=nieuwe_naam)
        )
    return resultaat.rowcount > 0


def verwijder_eigen_winkel(engine: Engine, organisatie_id: int, eigen_winkel_id: int) -> bool:
    """Verwijdert de winkel en, in dezelfde transactie, al zijn
    verkoopdata + instellingen — zelfde reden als db.organisaties.
    verwijder_organisatie(): nooit een tussentoestand met wees-rijen."""
    with engine.begin() as conn:
        rij = conn.execute(
            select(eigen_winkels.c.id).where(
                eigen_winkels.c.id == eigen_winkel_id, eigen_winkels.c.organisatie_id == organisatie_id
            )
        ).first()
        if rij is None:
            return False
        conn.execute(eigen_verkoopdata.delete().where(eigen_verkoopdata.c.eigen_winkel_id == eigen_winkel_id))
        conn.execute(
            eigen_product_verkoopdata.delete().where(eigen_product_verkoopdata.c.eigen_winkel_id == eigen_winkel_id)
        )
        conn.execute(
            eigen_winkel_instellingen.delete().where(eigen_winkel_instellingen.c.eigen_winkel_id == eigen_winkel_id)
        )
        conn.execute(eigen_winkels.delete().where(eigen_winkels.c.id == eigen_winkel_id))
    return True
