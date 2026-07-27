from db.bootstrap import bootstrap_organisatie
from db.gebruikers import haal_gebruiker, maak_gebruiker, verifieer_inloggegevens
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


def test_haal_gebruiker_binnen_eigen_organisatie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    gebruiker_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@klant.nl", wachtwoord="x", rol="lid")

    rij = haal_gebruiker(engine, gebruiker_id=gebruiker_id, organisatie_id=org_id)

    assert rij is not None
    assert rij.email == "lid@klant.nl"
    assert rij.rol == "lid"


def test_haal_gebruiker_andere_organisatie_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Org A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Org B", slug="org-b", store_ids=[])
    gebruiker_id = maak_gebruiker(engine, organisatie_id=org_a, email="lid@klant.nl", wachtwoord="x", rol="lid")

    assert haal_gebruiker(engine, gebruiker_id=gebruiker_id, organisatie_id=org_b) is None


def test_haal_gebruiker_onbekend_id_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    assert haal_gebruiker(engine, gebruiker_id=999, organisatie_id=org_id) is None
