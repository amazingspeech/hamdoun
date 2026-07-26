import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.bootstrap import bootstrap_organisatie
from db.schema import maak_database, organisaties, winkels


def test_bootstrap_organisatie_zonder_winkels_maakt_alleen_de_organisatie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    org_id = bootstrap_organisatie(engine, naam="Lege klant", slug="lege-klant", store_ids=[])

    with engine.connect() as conn:
        aantal_winkels = conn.execute(
            select(winkels).where(winkels.c.organisatie_id == org_id)
        ).all()
        assert aantal_winkels == []


def test_bootstrap_organisatie_dubbele_slug_faalt_hard(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    bootstrap_organisatie(engine, naam="Eerste", slug="klant", store_ids=[])

    with pytest.raises(IntegrityError):
        bootstrap_organisatie(engine, naam="Tweede", slug="klant", store_ids=[])


def test_bootstrap_organisatie_maakt_organisatie_met_gekoppelde_winkels(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    org_id = bootstrap_organisatie(engine, naam="Bestaande klant", slug="bestaande-klant", store_ids=[1, 2, 5])

    with engine.connect() as conn:
        org_rij = conn.execute(select(organisaties).where(organisaties.c.id == org_id)).one()
        assert org_rij.naam == "Bestaande klant"
        assert org_rij.slug == "bestaande-klant"
        assert org_rij.actief is True

        gekoppelde_store_ids = {
            rij.extern_store_id
            for rij in conn.execute(select(winkels).where(winkels.c.organisatie_id == org_id))
        }
        assert gekoppelde_store_ids == {1, 2, 5}
