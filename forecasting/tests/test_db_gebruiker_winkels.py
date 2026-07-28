from db.bootstrap import bootstrap_organisatie
from db.gebruiker_winkels import (
    hoort_winkel_bij_toewijzing,
    lijst_toegewezen_winkels,
    migreer_bestaande_leden,
    stel_toewijzingen_in,
)
from db.gebruikers import maak_gebruiker
from db.schema import maak_database


def test_stel_toewijzingen_in_en_lijst_terug(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[1, 2, 3])
    gebruiker_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@test.nl", wachtwoord="x", rol="lid")

    stel_toewijzingen_in(engine, gebruiker_id=gebruiker_id, extern_store_ids=[1, 2])

    assert set(lijst_toegewezen_winkels(engine, gebruiker_id=gebruiker_id)) == {1, 2}


def test_stel_toewijzingen_in_vervangt_bestaande_set(tmp_path):
    """Een tweede aanroep vervangt de vorige toewijzing volledig — geen
    optelling van oude en nieuwe winkels."""
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[1, 2, 3])
    gebruiker_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@test.nl", wachtwoord="x", rol="lid")

    stel_toewijzingen_in(engine, gebruiker_id=gebruiker_id, extern_store_ids=[1, 2])
    stel_toewijzingen_in(engine, gebruiker_id=gebruiker_id, extern_store_ids=[3])

    assert lijst_toegewezen_winkels(engine, gebruiker_id=gebruiker_id) == [3]


def test_stel_toewijzingen_in_lege_lijst_verwijdert_alles(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[1])
    gebruiker_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@test.nl", wachtwoord="x", rol="lid")
    stel_toewijzingen_in(engine, gebruiker_id=gebruiker_id, extern_store_ids=[1])

    stel_toewijzingen_in(engine, gebruiker_id=gebruiker_id, extern_store_ids=[])

    assert lijst_toegewezen_winkels(engine, gebruiker_id=gebruiker_id) == []


def test_hoort_winkel_bij_toewijzing_ware_toewijzing(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[1, 2])
    gebruiker_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@test.nl", wachtwoord="x", rol="lid")
    stel_toewijzingen_in(engine, gebruiker_id=gebruiker_id, extern_store_ids=[1])

    assert hoort_winkel_bij_toewijzing(engine, gebruiker_id=gebruiker_id, extern_store_id=1) is True
    assert hoort_winkel_bij_toewijzing(engine, gebruiker_id=gebruiker_id, extern_store_id=2) is False


def test_toewijzingen_zijn_ge_isoleerd_per_gebruiker(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[1, 2])
    lid_a = maak_gebruiker(engine, organisatie_id=org_id, email="a@test.nl", wachtwoord="x", rol="lid")
    lid_b = maak_gebruiker(engine, organisatie_id=org_id, email="b@test.nl", wachtwoord="x", rol="lid")
    stel_toewijzingen_in(engine, gebruiker_id=lid_a, extern_store_ids=[1])
    stel_toewijzingen_in(engine, gebruiker_id=lid_b, extern_store_ids=[2])

    assert lijst_toegewezen_winkels(engine, gebruiker_id=lid_a) == [1]
    assert lijst_toegewezen_winkels(engine, gebruiker_id=lid_b) == [2]


def test_migreer_bestaande_leden_koppelt_aan_alle_huidige_org_winkels(tmp_path):
    """Zonder deze migratie zou elk bestaand lid bij invoering van dit
    systeem direct alle toegang verliezen — de migratie zorgt dat niemand
    op het moment van deploy iets verliest dat ze al hadden."""
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[1, 2, 3])
    lid_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@test.nl", wachtwoord="x", rol="lid")
    eigenaar_id = maak_gebruiker(
        engine, organisatie_id=org_id, email="eigenaar@test.nl", wachtwoord="x", rol="eigenaar"
    )

    aantal = migreer_bestaande_leden(engine)

    assert aantal == 1
    assert set(lijst_toegewezen_winkels(engine, gebruiker_id=lid_id)) == {1, 2, 3}
    # Een eigenaar krijgt nooit rijen — die heeft toegang los van deze tabel.
    assert lijst_toegewezen_winkels(engine, gebruiker_id=eigenaar_id) == []


def test_migreer_bestaande_leden_is_idempotent(tmp_path):
    """Een lid dat al een (eventueel bewust ingeperkte) toewijzing heeft
    wordt overgeslagen — een tweede migratie-run mag geen eerdere
    inperking teruggedraaien naar 'alles'."""
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[1, 2])
    lid_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@test.nl", wachtwoord="x", rol="lid")
    stel_toewijzingen_in(engine, gebruiker_id=lid_id, extern_store_ids=[1])

    aantal = migreer_bestaande_leden(engine)

    assert aantal == 0
    assert lijst_toegewezen_winkels(engine, gebruiker_id=lid_id) == [1]
