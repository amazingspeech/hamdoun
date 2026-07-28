import pytest

from db import gebruikers_cli
from db.bootstrap import bootstrap_organisatie
from db.gebruikers import verifieer_inloggegevens
from db.schema import maak_database


def test_cli_maakt_gebruiker_die_kan_inloggen(tmp_path):
    database_pad = tmp_path / "tenants.db"
    engine = maak_database(database_pad)
    bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    gebruiker_id = gebruikers_cli.main([
        "--database-pad", str(database_pad),
        "--organisatie-slug", "klant",
        "--email", "eigenaar@klant.nl",
        "--wachtwoord", "een-goed-wachtwoord",
    ])

    assert verifieer_inloggegevens(engine, email="eigenaar@klant.nl", wachtwoord="een-goed-wachtwoord") == gebruiker_id


def test_cli_onbekende_slug_faalt_hard(tmp_path):
    database_pad = tmp_path / "tenants.db"
    maak_database(database_pad)

    with pytest.raises(RuntimeError, match="bestaat niet"):
        gebruikers_cli.main([
            "--database-pad", str(database_pad),
            "--organisatie-slug", "onbestaand",
            "--email", "eigenaar@klant.nl",
            "--wachtwoord", "een-goed-wachtwoord",
        ])
