"""Fase 5 premium (herbestel-advies per product): opslag voor
per-product verkoopdata, per eigen winkel (zie db/eigen_winkels.py — zie
serving/product_verkoopdata.py voor de CSV-parser)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import eigen_product_verkoopdata


def vervang_product_verkoopdata(engine: Engine, eigen_winkel_id: int, rijen: list[tuple[str, str, int]]) -> None:
    """Vervangt de volledige product-verkoopdata van een eigen winkel door
    precies de opgegeven rijen — zelfde vervang-i.p.v.-samenvoegen-gedrag
    als db.verkoopdata.vervang_verkoopdata."""
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            eigen_product_verkoopdata.delete().where(eigen_product_verkoopdata.c.eigen_winkel_id == eigen_winkel_id)
        )
        if not rijen:
            return
        conn.execute(
            eigen_product_verkoopdata.insert(),
            [{"eigen_winkel_id": eigen_winkel_id, "datum": datum, "product": product, "aantal": aantal, "aangemaakt_op": nu}
             for datum, product, aantal in rijen],
        )


def haal_product_verkoopdata(engine: Engine, eigen_winkel_id: int) -> list[dict]:
    with engine.connect() as conn:
        rijen = conn.execute(
            select(eigen_product_verkoopdata.c.datum, eigen_product_verkoopdata.c.product, eigen_product_verkoopdata.c.aantal)
            .where(eigen_product_verkoopdata.c.eigen_winkel_id == eigen_winkel_id)
            .order_by(eigen_product_verkoopdata.c.datum)
        ).all()
    return [{"datum": r.datum, "product": r.product, "aantal": r.aantal} for r in rijen]
