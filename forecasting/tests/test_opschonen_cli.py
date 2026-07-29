from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from db import opschonen_cli
from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.organisaties import deactiveer_organisatie
from db.schema import gebruikers, maak_database, organisaties


def _maak_gedeactiveerde_organisatie(engine, naam, slug, dagen_geleden):
    org_id = bootstrap_organisatie(engine, naam=naam, slug=slug, store_ids=[])
    deactiveer_organisatie(engine, organisatie_id=org_id)
    verleden = datetime.now(timezone.utc) - timedelta(days=dagen_geleden)
    with engine.begin() as conn:
        conn.execute(organisaties.update().where(organisaties.c.id == org_id).values(gedeactiveerd_op=verleden))
    return org_id


def test_main_verwijdert_organisatie_over_wachtperiode(tmp_path, monkeypatch):
    db_pad = tmp_path / "tenants.db"
    engine = maak_database(db_pad)
    org_id = _maak_gedeactiveerde_organisatie(engine, "Klant", "klant", dagen_geleden=31)
    monkeypatch.setenv("TENANTS_DB_PAD", str(db_pad))

    verwijderd = opschonen_cli.main()

    assert verwijderd == [org_id]
    with engine.connect() as conn:
        assert conn.execute(select(organisaties).where(organisaties.c.id == org_id)).first() is None


def test_main_laat_recent_gedeactiveerde_organisatie_staan(tmp_path, monkeypatch):
    db_pad = tmp_path / "tenants.db"
    engine = maak_database(db_pad)
    org_id = _maak_gedeactiveerde_organisatie(engine, "Klant", "klant", dagen_geleden=5)
    monkeypatch.setenv("TENANTS_DB_PAD", str(db_pad))

    verwijderd = opschonen_cli.main()

    assert verwijderd == []
    with engine.connect() as conn:
        assert conn.execute(select(organisaties).where(organisaties.c.id == org_id)).first() is not None


def test_main_gaat_door_na_fout_bij_een_organisatie(tmp_path, monkeypatch):
    db_pad = tmp_path / "tenants.db"
    engine = maak_database(db_pad)
    org_a = _maak_gedeactiveerde_organisatie(engine, "Org A", "org-a", dagen_geleden=31)
    org_b = _maak_gedeactiveerde_organisatie(engine, "Org B", "org-b", dagen_geleden=31)
    monkeypatch.setenv("TENANTS_DB_PAD", str(db_pad))

    origineel = opschonen_cli.verwijder_organisatie
    def _mislukt_voor_org_a(engine, organisatie_id):
        if organisatie_id == org_a:
            raise RuntimeError("gesimuleerde databasefout")
        origineel(engine, organisatie_id)
    monkeypatch.setattr(opschonen_cli, "verwijder_organisatie", _mislukt_voor_org_a)

    verwijderd = opschonen_cli.main()

    assert verwijderd == [org_b]


def test_main_logt_geen_naam_of_email(tmp_path, monkeypatch, capsys):
    db_pad = tmp_path / "tenants.db"
    engine = maak_database(db_pad)
    org_id = _maak_gedeactiveerde_organisatie(engine, "Geheime Bakkerij BV", "geheime-bakkerij", dagen_geleden=31)
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@geheimebakkerij.nl", wachtwoord="geheim123")
    # verwijder_organisatie() draait vóór het printen, dus de e-mail bestaat
    # op het moment van loggen niet meer in de database — deze test bevestigt
    # bovendien dat de geloggde tekst zelf die waarden nooit noemt.
    monkeypatch.setenv("TENANTS_DB_PAD", str(db_pad))

    opschonen_cli.main()

    output = capsys.readouterr().out
    assert "Geheime Bakkerij BV" not in output
    assert "eigenaar@geheimebakkerij.nl" not in output
    assert str(org_id) in output
