from db.bootstrap import bootstrap_organisatie
from db.gebruikers import (
    email_is_in_gebruik,
    haal_eigenaar_email,
    haal_gebruiker,
    maak_gebruiker,
    maak_gebruiker_met_hash,
    verifieer_inloggegevens,
    vind_gebruiker_id_via_email,
    wijzig_wachtwoord,
)
from db.schema import maak_database
from security.api_keys import hash_key


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


def test_maak_gebruiker_met_hash_slaat_geen_nieuw_hashformaat_op(tmp_path):
    """maak_gebruiker_met_hash() bestaat voor de self-serve signup-flow
    (Fase 5 NODIG 5), waar het wachtwoord al gehasht is op het moment dat de
    aanmelding werd gestart (vóór de Stripe-redirect) — dus geen tweede keer
    hashen hier, alleen opslaan. Test bevestigt dat het resultaat nog steeds
    verifieerbaar is via de bestaande login-functie, dus geen nieuw formaat."""
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    hash_hex, salt_hex = hash_key("correct-paard")

    gebruiker_id = maak_gebruiker_met_hash(
        engine, organisatie_id=org_id, email="eigenaar@klant.nl",
        wachtwoord_hash=hash_hex, wachtwoord_salt=salt_hex, rol="eigenaar",
    )

    assert verifieer_inloggegevens(engine, email="eigenaar@klant.nl", wachtwoord="correct-paard") == gebruiker_id
    rij = haal_gebruiker(engine, gebruiker_id=gebruiker_id, organisatie_id=org_id)
    assert rij.rol == "eigenaar"


def test_email_is_in_gebruik_bestaand_email(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="bezet@klant.nl", wachtwoord="x")

    assert email_is_in_gebruik(engine, email="bezet@klant.nl") is True


def test_email_is_in_gebruik_onbekend_email(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    assert email_is_in_gebruik(engine, email="vrij@klant.nl") is False


def test_haal_eigenaar_email_geeft_email_van_de_eigenaar(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="lid@klant.nl", wachtwoord="x", rol="lid")
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@klant.nl", wachtwoord="x", rol="eigenaar")

    assert haal_eigenaar_email(engine, organisatie_id=org_id) == "eigenaar@klant.nl"


def test_haal_eigenaar_email_zonder_eigenaar_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    assert haal_eigenaar_email(engine, organisatie_id=org_id) is None


def test_vind_gebruiker_id_via_email_bestaand_email(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    gebruiker_id = maak_gebruiker(engine, organisatie_id=org_id, email="test@klant.nl", wachtwoord="x")

    assert vind_gebruiker_id_via_email(engine, email="test@klant.nl") == gebruiker_id


def test_vind_gebruiker_id_via_email_onbekend_email(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    assert vind_gebruiker_id_via_email(engine, email="onbekend@klant.nl") is None


def test_vind_gebruiker_id_via_email_negeert_inactieve_gebruiker(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="test@klant.nl", wachtwoord="x")
    from db.schema import gebruikers
    with engine.begin() as conn:
        conn.execute(gebruikers.update().where(gebruikers.c.email == "test@klant.nl").values(actief=False))

    assert vind_gebruiker_id_via_email(engine, email="test@klant.nl") is None


def test_wijzig_wachtwoord(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    gebruiker_id = maak_gebruiker(engine, organisatie_id=org_id, email="test@klant.nl", wachtwoord="oud-wachtwoord")

    wijzig_wachtwoord(engine, gebruiker_id=gebruiker_id, nieuw_wachtwoord="nieuw-wachtwoord")

    assert verifieer_inloggegevens(engine, email="test@klant.nl", wachtwoord="oud-wachtwoord") is None
    assert verifieer_inloggegevens(engine, email="test@klant.nl", wachtwoord="nieuw-wachtwoord") == gebruiker_id


def test_aantal_actieve_gebruikers(tmp_path):
    from db.bootstrap import bootstrap_organisatie
    from db.gebruikers import aantal_actieve_gebruikers, maak_gebruiker
    from db.schema import maak_database

    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@voorbeeld.nl", wachtwoord="wachtwoord-1", rol="eigenaar")
    maak_gebruiker(engine, organisatie_id=org_id, email="lid@voorbeeld.nl", wachtwoord="wachtwoord-2", rol="lid")

    assert aantal_actieve_gebruikers(engine, org_id) == 2


def test_aantal_actieve_gebruikers_negeert_andere_organisatie(tmp_path):
    from db.bootstrap import bootstrap_organisatie
    from db.gebruikers import aantal_actieve_gebruikers, maak_gebruiker
    from db.schema import maak_database

    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Organisatie B", slug="org-b", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_a, email="eigenaar-a@voorbeeld.nl", wachtwoord="wachtwoord-1", rol="eigenaar")
    maak_gebruiker(engine, organisatie_id=org_b, email="eigenaar-b@voorbeeld.nl", wachtwoord="wachtwoord-2", rol="eigenaar")

    assert aantal_actieve_gebruikers(engine, org_a) == 1
