from db.bootstrap import bootstrap_organisatie
from db.eigen_winkels import maak_eigen_winkel
from db.product_verkoopdata import haal_product_verkoopdata, vervang_product_verkoopdata
from db.schema import maak_database


def test_vervang_product_verkoopdata_en_teruglezen(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    vervang_product_verkoopdata(
        engine, eigen_winkel_id=winkel_id,
        rijen=[("2026-01-01", "Brood", 10), ("2026-01-01", "Melk", 4)],
    )

    assert haal_product_verkoopdata(engine, eigen_winkel_id=winkel_id) == [
        {"datum": "2026-01-01", "product": "Brood", "aantal": 10},
        {"datum": "2026-01-01", "product": "Melk", "aantal": 4},
    ]


def test_vervang_product_verkoopdata_vervangt_volledig(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")
    vervang_product_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=[("2026-01-01", "Brood", 10)])

    vervang_product_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=[("2026-02-01", "Melk", 3)])

    assert haal_product_verkoopdata(engine, eigen_winkel_id=winkel_id) == [
        {"datum": "2026-02-01", "product": "Melk", "aantal": 3},
    ]


def test_product_verkoopdata_geeft_gesorteerd_op_datum_terug(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    vervang_product_verkoopdata(
        engine, eigen_winkel_id=winkel_id,
        rijen=[("2026-01-03", "Brood", 1), ("2026-01-01", "Brood", 2), ("2026-01-02", "Brood", 3)],
    )

    datums = [r["datum"] for r in haal_product_verkoopdata(engine, eigen_winkel_id=winkel_id)]
    assert datums == ["2026-01-01", "2026-01-02", "2026-01-03"]


def test_zonder_product_verkoopdata_geeft_lege_lijst(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    assert haal_product_verkoopdata(engine, eigen_winkel_id=winkel_id) == []


def test_product_verkoopdata_is_geisoleerd_per_eigen_winkel(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_a = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")
    winkel_b = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop B")
    vervang_product_verkoopdata(engine, eigen_winkel_id=winkel_a, rijen=[("2026-01-01", "Brood", 10)])

    assert haal_product_verkoopdata(engine, eigen_winkel_id=winkel_b) == []
