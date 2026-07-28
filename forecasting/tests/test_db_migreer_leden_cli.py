from db import migreer_leden_cli
from db.bootstrap import bootstrap_organisatie
from db.gebruiker_winkels import lijst_toegewezen_winkels
from db.gebruikers import maak_gebruiker
from db.schema import maak_database


def test_migreer_leden_cli_koppelt_bestaande_leden_aan_hun_winkels(tmp_path):
    database_pad = tmp_path / "tenants.db"
    engine = maak_database(database_pad)
    org_id = bootstrap_organisatie(engine, naam="Bestaande klant", slug="bestaande-klant", store_ids=[1, 2])
    lid_id = maak_gebruiker(engine, organisatie_id=org_id, email="lid@test.nl", wachtwoord="x", rol="lid")

    aantal = migreer_leden_cli.main(["--database-pad", str(database_pad)])

    assert aantal == 1
    assert set(lijst_toegewezen_winkels(engine, gebruiker_id=lid_id)) == {1, 2}
