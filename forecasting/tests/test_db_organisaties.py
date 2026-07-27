from db.bootstrap import bootstrap_organisatie
from db.organisaties import haal_gemiddelde_omzet_per_stuk, stel_gemiddelde_omzet_per_stuk_in
from db.schema import maak_database


def test_zonder_ingestelde_prijs_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    assert haal_gemiddelde_omzet_per_stuk(engine, organisatie_id=org_id) is None


def test_prijs_instellen_en_teruglezen(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    stel_gemiddelde_omzet_per_stuk_in(engine, organisatie_id=org_id, bedrag=12.5)

    assert haal_gemiddelde_omzet_per_stuk(engine, organisatie_id=org_id) == 12.5


def test_prijs_instellen_overschrijft_vorige_waarde(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    stel_gemiddelde_omzet_per_stuk_in(engine, organisatie_id=org_id, bedrag=12.5)

    stel_gemiddelde_omzet_per_stuk_in(engine, organisatie_id=org_id, bedrag=9.0)

    assert haal_gemiddelde_omzet_per_stuk(engine, organisatie_id=org_id) == 9.0


def test_prijs_is_geisoleerd_per_organisatie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Org A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Org B", slug="org-b", store_ids=[])
    stel_gemiddelde_omzet_per_stuk_in(engine, organisatie_id=org_a, bedrag=12.5)

    assert haal_gemiddelde_omzet_per_stuk(engine, organisatie_id=org_b) is None
