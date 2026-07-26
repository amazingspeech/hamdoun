from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker, verifieer_inloggegevens
from db.schema import maak_database


def test_verifieer_inloggegevens_met_juist_wachtwoord(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    gebruiker_id = maak_gebruiker(engine, organisatie_id=org_id, email="test@voorbeeld.nl", wachtwoord="correct-paard")

    resultaat = verifieer_inloggegevens(engine, email="test@voorbeeld.nl", wachtwoord="correct-paard")

    assert resultaat == gebruiker_id


def test_verifieer_inloggegevens_met_fout_wachtwoord(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="test@voorbeeld.nl", wachtwoord="correct-paard")

    assert verifieer_inloggegevens(engine, email="test@voorbeeld.nl", wachtwoord="fout") is None


def test_verifieer_inloggegevens_onbekend_email(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    assert verifieer_inloggegevens(engine, email="bestaat-niet@voorbeeld.nl", wachtwoord="wat-dan-ook") is None


def test_verifieer_inloggegevens_negeert_inactieve_gebruiker(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="test@voorbeeld.nl", wachtwoord="correct-paard")

    from db.schema import gebruikers
    with engine.begin() as conn:
        conn.execute(gebruikers.update().where(gebruikers.c.email == "test@voorbeeld.nl").values(actief=False))

    assert verifieer_inloggegevens(engine, email="test@voorbeeld.nl", wachtwoord="correct-paard") is None
