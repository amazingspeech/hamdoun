
from sqlalchemy import select

from db.api_keys import deactiveer_api_key, lijst_api_keys, maak_api_key, migreer_bestaande_key, vind_organisatie_voor_key
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


def test_maak_api_key_geeft_werkende_ruwe_key_terug(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    key_id, ruwe_key = maak_api_key(engine, organisatie_id=org_id, naam="Kassasysteem")

    assert vind_organisatie_voor_key(engine, ruwe_key) == ("Kassasysteem", org_id)
    assert isinstance(key_id, int)


def test_lijst_api_keys_toont_alleen_eigen_organisatie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Organisatie B", slug="org-b", store_ids=[])
    maak_api_key(engine, organisatie_id=org_a, naam="key-a")
    maak_api_key(engine, organisatie_id=org_b, naam="key-b")

    lijst = lijst_api_keys(engine, organisatie_id=org_a)

    namen = {rij.naam for rij in lijst}
    assert namen == {"key-a"}


def test_lijst_api_keys_bevat_geen_hash_of_salt(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    maak_api_key(engine, organisatie_id=org_id, naam="key-a")

    lijst = lijst_api_keys(engine, organisatie_id=org_id)

    assert not hasattr(lijst[0], "hash")
    assert not hasattr(lijst[0], "salt")


def test_deactiveer_api_key_maakt_key_ongeldig(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    key_id, ruwe_key = maak_api_key(engine, organisatie_id=org_id, naam="key-a")

    assert deactiveer_api_key(engine, organisatie_id=org_id, key_id=key_id) is True
    assert vind_organisatie_voor_key(engine, ruwe_key) is None


def test_deactiveer_api_key_andere_organisatie_faalt(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Organisatie B", slug="org-b", store_ids=[])
    key_id, ruwe_key = maak_api_key(engine, organisatie_id=org_a, naam="key-a")

    assert deactiveer_api_key(engine, organisatie_id=org_b, key_id=key_id) is False
    assert vind_organisatie_voor_key(engine, ruwe_key) is not None
