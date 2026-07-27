from db.bootstrap import bootstrap_organisatie
from db.schema import maak_database
from db.verkoopdata import haal_verkoopdata, vervang_verkoopdata


def test_vervang_verkoopdata_en_teruglezen(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    vervang_verkoopdata(engine, organisatie_id=org_id, rijen=[("2026-01-01", 100.0), ("2026-01-02", 150.5)])

    assert haal_verkoopdata(engine, organisatie_id=org_id) == [
        {"datum": "2026-01-01", "omzet": 100.0},
        {"datum": "2026-01-02", "omzet": 150.5},
    ]


def test_vervang_verkoopdata_vervangt_volledig(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    vervang_verkoopdata(engine, organisatie_id=org_id, rijen=[("2026-01-01", 100.0)])

    vervang_verkoopdata(engine, organisatie_id=org_id, rijen=[("2026-02-01", 200.0)])

    assert haal_verkoopdata(engine, organisatie_id=org_id) == [{"datum": "2026-02-01", "omzet": 200.0}]


def test_verkoopdata_geeft_gesorteerd_op_datum_terug(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    vervang_verkoopdata(
        engine, organisatie_id=org_id,
        rijen=[("2026-01-03", 1.0), ("2026-01-01", 2.0), ("2026-01-02", 3.0)],
    )

    datums = [r["datum"] for r in haal_verkoopdata(engine, organisatie_id=org_id)]
    assert datums == ["2026-01-01", "2026-01-02", "2026-01-03"]


def test_zonder_verkoopdata_geeft_lege_lijst(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    assert haal_verkoopdata(engine, organisatie_id=org_id) == []


def test_verkoopdata_is_geisoleerd_per_organisatie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Org A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Org B", slug="org-b", store_ids=[])
    vervang_verkoopdata(engine, organisatie_id=org_a, rijen=[("2026-01-01", 100.0)])

    assert haal_verkoopdata(engine, organisatie_id=org_b) == []
