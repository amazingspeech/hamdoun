from db.bootstrap import bootstrap_organisatie
from db.eigen_winkels import maak_eigen_winkel
from db.schema import maak_database
from db.verkoopdata import haal_verkoopdata, vervang_verkoopdata


def test_vervang_verkoopdata_en_teruglezen(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    vervang_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=[("2026-01-01", 100.0), ("2026-01-02", 150.5)])

    assert haal_verkoopdata(engine, eigen_winkel_id=winkel_id) == [
        {"datum": "2026-01-01", "omzet": 100.0},
        {"datum": "2026-01-02", "omzet": 150.5},
    ]


def test_vervang_verkoopdata_vervangt_volledig(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")
    vervang_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=[("2026-01-01", 100.0)])

    vervang_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=[("2026-02-01", 200.0)])

    assert haal_verkoopdata(engine, eigen_winkel_id=winkel_id) == [{"datum": "2026-02-01", "omzet": 200.0}]


def test_verkoopdata_geeft_gesorteerd_op_datum_terug(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    vervang_verkoopdata(
        engine, eigen_winkel_id=winkel_id,
        rijen=[("2026-01-03", 1.0), ("2026-01-01", 2.0), ("2026-01-02", 3.0)],
    )

    datums = [r["datum"] for r in haal_verkoopdata(engine, eigen_winkel_id=winkel_id)]
    assert datums == ["2026-01-01", "2026-01-02", "2026-01-03"]


def test_zonder_verkoopdata_geeft_lege_lijst(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    assert haal_verkoopdata(engine, eigen_winkel_id=winkel_id) == []


def test_verkoopdata_is_geisoleerd_per_eigen_winkel(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_a = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")
    winkel_b = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop B")
    vervang_verkoopdata(engine, eigen_winkel_id=winkel_a, rijen=[("2026-01-01", 100.0)])

    assert haal_verkoopdata(engine, eigen_winkel_id=winkel_b) == []
