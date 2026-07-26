
from sqlalchemy import select

from db.api_keys import migreer_bestaande_key
from db.bootstrap import bootstrap_organisatie
from db.schema import api_keys, maak_database


def test_migreer_bestaande_key_zet_hash_en_salt_ongewijzigd_over(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    key_id = migreer_bestaande_key(
        engine, organisatie_id=org_id, naam="lokaal-testen", hash="abc123hash", salt="def456salt",
    )

    with engine.connect() as conn:
        rij = conn.execute(select(api_keys).where(api_keys.c.id == key_id)).one()
        assert rij.organisatie_id == org_id
        assert rij.naam == "lokaal-testen"
        assert rij.hash == "abc123hash"
        assert rij.salt == "def456salt"
        assert rij.actief is True
