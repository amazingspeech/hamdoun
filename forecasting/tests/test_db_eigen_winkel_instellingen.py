from db.bootstrap import bootstrap_organisatie
from db.eigen_winkel_instellingen import haal_prijs, stel_prijs_in
from db.eigen_winkels import maak_eigen_winkel
from db.schema import maak_database


def test_haal_prijs_zonder_instelling_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    assert haal_prijs(engine, eigen_winkel_id=winkel_id) is None


def test_stel_prijs_in_en_haal_weer_op(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    stel_prijs_in(engine, eigen_winkel_id=winkel_id, bedrag=24.5)

    assert haal_prijs(engine, eigen_winkel_id=winkel_id) == 24.5


def test_stel_prijs_in_overschrijft_bestaande_waarde(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")
    stel_prijs_in(engine, eigen_winkel_id=winkel_id, bedrag=24.5)

    stel_prijs_in(engine, eigen_winkel_id=winkel_id, bedrag=30.0)

    assert haal_prijs(engine, eigen_winkel_id=winkel_id) == 30.0
