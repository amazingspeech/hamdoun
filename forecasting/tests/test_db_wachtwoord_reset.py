from datetime import timedelta

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database, wachtwoord_reset_tokens
from db.wachtwoord_reset import maak_reset_token, markeer_reset_token_gebruikt, vind_gebruiker_voor_reset_token


def _gebruiker(engine):
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    return maak_gebruiker(engine, organisatie_id=org_id, email="test@klant.nl", wachtwoord="oud-wachtwoord")


def test_maak_reset_token_kan_teruggevonden_worden(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    gebruiker_id = _gebruiker(engine)

    token = maak_reset_token(engine, gebruiker_id=gebruiker_id)

    assert vind_gebruiker_voor_reset_token(engine, token) == gebruiker_id


def test_onbekend_token_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    assert vind_gebruiker_voor_reset_token(engine, "bestaat-niet") is None


def test_verlopen_token_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    gebruiker_id = _gebruiker(engine)

    token = maak_reset_token(engine, gebruiker_id=gebruiker_id, geldigheidsduur=timedelta(hours=-1))

    assert vind_gebruiker_voor_reset_token(engine, token) is None


def test_gebruikt_token_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    gebruiker_id = _gebruiker(engine)
    token = maak_reset_token(engine, gebruiker_id=gebruiker_id)

    markeer_reset_token_gebruikt(engine, token)

    assert vind_gebruiker_voor_reset_token(engine, token) is None


def test_markeer_reset_token_gebruikt_zet_gebruikt_op(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    gebruiker_id = _gebruiker(engine)
    token = maak_reset_token(engine, gebruiker_id=gebruiker_id)

    markeer_reset_token_gebruikt(engine, token)

    from sqlalchemy import select
    with engine.connect() as conn:
        rij = conn.execute(select(wachtwoord_reset_tokens)).one()
    assert rij.gebruikt_op is not None
