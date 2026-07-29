import pytest
from sqlalchemy.exc import IntegrityError

from db.bootstrap import bootstrap_organisatie
from db.eigen_winkels import (
    hernoem_eigen_winkel,
    lijst_eigen_winkels,
    maak_eigen_winkel,
    verwijder_eigen_winkel,
)
from db.schema import eigen_verkoopdata, maak_database
from db.verkoopdata import vervang_verkoopdata


def test_maak_eigen_winkel_geeft_nieuw_id_terug(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    assert isinstance(winkel_id, int)


def test_maak_eigen_winkel_dubbele_naam_binnen_organisatie_faalt(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    with pytest.raises(IntegrityError):
        maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")


def test_maak_eigen_winkel_zelfde_naam_andere_organisatie_mag(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Klant A", slug="klant-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Klant B", slug="klant-b", store_ids=[])
    maak_eigen_winkel(engine, organisatie_id=org_a, naam="Webshop A")

    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_b, naam="Webshop A")

    assert isinstance(winkel_id, int)


def test_lijst_eigen_winkels_geeft_alleen_winkels_van_die_organisatie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Klant A", slug="klant-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Klant B", slug="klant-b", store_ids=[])
    maak_eigen_winkel(engine, organisatie_id=org_a, naam="Webshop A")
    maak_eigen_winkel(engine, organisatie_id=org_b, naam="Webshop B")

    winkels = lijst_eigen_winkels(engine, organisatie_id=org_a)

    assert [w["naam"] for w in winkels] == ["Webshop A"]


def test_lijst_eigen_winkels_heeft_verkoopdata_klopt(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    winkels = lijst_eigen_winkels(engine, organisatie_id=org_id)
    assert winkels[0]["heeft_verkoopdata"] is False

    vervang_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=[("2026-06-01", 100.0)])
    winkels = lijst_eigen_winkels(engine, organisatie_id=org_id)
    assert winkels[0]["heeft_verkoopdata"] is True


def test_hernoem_eigen_winkel_wijzigt_naam(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    gelukt = hernoem_eigen_winkel(engine, organisatie_id=org_id, eigen_winkel_id=winkel_id, nieuwe_naam="Webshop B")

    assert gelukt is True
    assert lijst_eigen_winkels(engine, organisatie_id=org_id)[0]["naam"] == "Webshop B"


def test_hernoem_eigen_winkel_andere_organisatie_geeft_false(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Klant A", slug="klant-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Klant B", slug="klant-b", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_a, naam="Webshop A")

    gelukt = hernoem_eigen_winkel(engine, organisatie_id=org_b, eigen_winkel_id=winkel_id, nieuwe_naam="Overname")

    assert gelukt is False
    assert lijst_eigen_winkels(engine, organisatie_id=org_a)[0]["naam"] == "Webshop A"


def test_verwijder_eigen_winkel_verwijdert_ook_verkoopdata(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")
    vervang_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=[("2026-06-01", 100.0)])

    gelukt = verwijder_eigen_winkel(engine, organisatie_id=org_id, eigen_winkel_id=winkel_id)

    assert gelukt is True
    assert lijst_eigen_winkels(engine, organisatie_id=org_id) == []
    with engine.connect() as conn:
        from sqlalchemy import select
        assert conn.execute(select(eigen_verkoopdata)).all() == []


def test_verwijder_eigen_winkel_andere_organisatie_geeft_false(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Klant A", slug="klant-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Klant B", slug="klant-b", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_a, naam="Webshop A")

    gelukt = verwijder_eigen_winkel(engine, organisatie_id=org_b, eigen_winkel_id=winkel_id)

    assert gelukt is False
    assert len(lijst_eigen_winkels(engine, organisatie_id=org_a)) == 1
