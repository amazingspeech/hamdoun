from db.bootstrap import bootstrap_organisatie
from db.schema import maak_database
from db.winkels import hoort_store_bij_organisatie


def test_hoort_store_bij_organisatie_ware_koppeling(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[1, 2])

    assert hoort_store_bij_organisatie(engine, store_id=1, organisatie_id=org_id) is True


def test_hoort_store_bij_organisatie_andere_organisatie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Org A", slug="org-a", store_ids=[1])
    org_b = bootstrap_organisatie(engine, naam="Org B", slug="org-b", store_ids=[2])

    assert hoort_store_bij_organisatie(engine, store_id=2, organisatie_id=org_a) is False
    assert hoort_store_bij_organisatie(engine, store_id=1, organisatie_id=org_b) is False


def test_hoort_store_bij_organisatie_onbekend_store_id(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[1])

    assert hoort_store_bij_organisatie(engine, store_id=999, organisatie_id=org_id) is False
