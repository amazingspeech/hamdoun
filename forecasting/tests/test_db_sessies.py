from datetime import datetime, timedelta, timezone

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database, sessies
from db.sessies import maak_sessie, verwijder_sessie, verwijder_sessies_voor_gebruiker, vind_gebruiker_voor_sessie


def _gebruiker(engine):
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    return maak_gebruiker(engine, organisatie_id=org_id, email="test@voorbeeld.nl", wachtwoord="correct-paard")


def test_maak_sessie_en_vind_gebruiker_voor_sessie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    gebruiker_id = _gebruiker(engine)

    ruwe_token = maak_sessie(engine, gebruiker_id=gebruiker_id)

    assert vind_gebruiker_voor_sessie(engine, ruwe_token) == gebruiker_id


def test_vind_gebruiker_voor_sessie_onbekende_token(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    assert vind_gebruiker_voor_sessie(engine, "bestaat-niet") is None


def test_vind_gebruiker_voor_sessie_verlopen_token(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    gebruiker_id = _gebruiker(engine)
    ruwe_token = maak_sessie(engine, gebruiker_id=gebruiker_id)

    verleden = datetime.now(timezone.utc) - timedelta(hours=1)
    with engine.begin() as conn:
        conn.execute(sessies.update().values(verloopt_op=verleden))

    assert vind_gebruiker_voor_sessie(engine, ruwe_token) is None


def test_verwijder_sessie_maakt_token_ongeldig(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    gebruiker_id = _gebruiker(engine)
    ruwe_token = maak_sessie(engine, gebruiker_id=gebruiker_id)

    verwijder_sessie(engine, ruwe_token)

    assert vind_gebruiker_voor_sessie(engine, ruwe_token) is None


def test_verwijder_sessies_voor_gebruiker_maakt_alle_tokens_van_die_gebruiker_ongeldig(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    gebruiker_id = _gebruiker(engine)
    token_1 = maak_sessie(engine, gebruiker_id=gebruiker_id)
    token_2 = maak_sessie(engine, gebruiker_id=gebruiker_id)

    verwijder_sessies_voor_gebruiker(engine, gebruiker_id=gebruiker_id)

    assert vind_gebruiker_voor_sessie(engine, token_1) is None
    assert vind_gebruiker_voor_sessie(engine, token_2) is None


def test_verwijder_sessies_voor_gebruiker_laat_andere_gebruikers_met_rust(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant-2", store_ids=[])
    andere_gebruiker_id = maak_gebruiker(engine, organisatie_id=org_id, email="ander@voorbeeld.nl", wachtwoord="x")
    andere_token = maak_sessie(engine, gebruiker_id=andere_gebruiker_id)
    gebruiker_id = _gebruiker(engine)

    verwijder_sessies_voor_gebruiker(engine, gebruiker_id=gebruiker_id)

    assert vind_gebruiker_voor_sessie(engine, andere_token) == andere_gebruiker_id
