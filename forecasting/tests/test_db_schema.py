from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from db.schema import maak_database, organisaties, winkels


def test_maak_database_maakt_organisaties_en_winkels_tabellen(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    tabellen = set(inspect(engine).get_table_names())
    assert {"organisaties", "winkels", "api_keys"} <= tabellen


def test_extern_store_id_moet_uniek_zijn(tmp_path):
    """Een winkel hoort in het huidige gedeelde-modelontwerp bij precies één
    organisatie (FASE4-SAAS-FOUNDATION.md, beslissing 4) — de database moet
    dat afdwingen, niet alleen applicatiecode."""
    engine = maak_database(tmp_path / "tenants.db")
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        org_id = conn.execute(
            organisaties.insert().values(naam="Org A", slug="org-a", actief=True, aangemaakt_op=nu)
        ).inserted_primary_key[0]
        conn.execute(
            winkels.insert().values(
                organisatie_id=org_id, extern_store_id=1, naam=None, actief=True, aangemaakt_op=nu
            )
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                winkels.insert().values(
                    organisatie_id=org_id, extern_store_id=1, naam=None, actief=True, aangemaakt_op=nu
                )
            )
