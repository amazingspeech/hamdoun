
import pytest
from sqlalchemy import create_engine, select

from db import migreer_keys_cli
from db.bootstrap import bootstrap_organisatie
from db.schema import api_keys, maak_database
from security import api_keys as security_api_keys


def test_migreer_keys_cli_onbekende_slug_faalt_hard(tmp_path):
    keys_pad = tmp_path / "api_keys.json"
    security_api_keys.voeg_key_toe(keys_pad, "klant-a", "ruwe-key-a")
    database_pad = tmp_path / "tenants.db"
    maak_database(database_pad)

    with pytest.raises(RuntimeError, match="bestaat niet"):
        migreer_keys_cli.main([
            "--api-keys-json", str(keys_pad),
            "--database-pad", str(database_pad),
            "--organisatie-slug", "onbestaand",
        ])


def test_migreer_keys_cli_zet_alle_keys_uit_json_over(tmp_path):
    keys_pad = tmp_path / "api_keys.json"
    security_api_keys.voeg_key_toe(keys_pad, "klant-a", "ruwe-key-a")
    security_api_keys.voeg_key_toe(keys_pad, "klant-b", "ruwe-key-b")

    database_pad = tmp_path / "tenants.db"
    engine = maak_database(database_pad)
    org_id = bootstrap_organisatie(engine, naam="Bestaande klant", slug="bestaande-klant", store_ids=[])

    aantal = migreer_keys_cli.main([
        "--api-keys-json", str(keys_pad),
        "--database-pad", str(database_pad),
        "--organisatie-slug", "bestaande-klant",
    ])
    assert aantal == 2

    controle_engine = create_engine(f"sqlite:///{database_pad}")
    with controle_engine.connect() as conn:
        namen = {rij.naam for rij in conn.execute(select(api_keys).where(api_keys.c.organisatie_id == org_id))}
    assert namen == {"klant-a", "klant-b"}
