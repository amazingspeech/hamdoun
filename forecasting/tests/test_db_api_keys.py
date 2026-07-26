
from sqlalchemy import select

from db.api_keys import migreer_bestaande_key, vind_organisatie_voor_key
from db.bootstrap import bootstrap_organisatie
from db.schema import api_keys, maak_database
from security.api_keys import hash_key


def test_vind_organisatie_voor_key_geeft_naam_en_organisatie_id_terug(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    hash_hex, salt_hex = hash_key("ruwe-key-123")
    migreer_bestaande_key(engine, organisatie_id=org_id, naam="klant-key", hash=hash_hex, salt=salt_hex)

    resultaat = vind_organisatie_voor_key(engine, "ruwe-key-123")

    assert resultaat is not None
    naam, organisatie_id = resultaat
    assert naam == "klant-key"
    assert organisatie_id == org_id


def test_vind_organisatie_voor_key_onbekende_key_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    assert vind_organisatie_voor_key(engine, "bestaat-niet") is None


def test_vind_organisatie_voor_key_negeert_inactieve_key(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    hash_hex, salt_hex = hash_key("ruwe-key-123")
    key_id = migreer_bestaande_key(engine, organisatie_id=org_id, naam="klant-key", hash=hash_hex, salt=salt_hex)
    with engine.begin() as conn:
        conn.execute(api_keys.update().where(api_keys.c.id == key_id).values(actief=False))

    assert vind_organisatie_voor_key(engine, "ruwe-key-123") is None


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
