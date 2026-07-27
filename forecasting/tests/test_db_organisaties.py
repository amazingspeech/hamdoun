from sqlalchemy import select

from db.bootstrap import bootstrap_organisatie
from db.organisaties import (
    haal_gemiddelde_omzet_per_stuk,
    lijst_actieve_organisaties,
    stel_gemiddelde_omzet_per_stuk_in,
    stel_stripe_koppeling_in,
)
from db.schema import maak_database, organisaties


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


def test_stel_stripe_koppeling_in(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    stel_stripe_koppeling_in(
        engine, organisatie_id=org_id, stripe_customer_id="cus_123", stripe_subscription_id="sub_456"
    )

    with engine.connect() as conn:
        rij = conn.execute(select(organisaties).where(organisaties.c.id == org_id)).one()
    assert rij.stripe_customer_id == "cus_123"
    assert rij.stripe_subscription_id == "sub_456"


def test_lijst_actieve_organisaties_geeft_alle_actieve_orgs(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Org A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Org B", slug="org-b", store_ids=[])

    orgs = lijst_actieve_organisaties(engine)

    ids = {o.id for o in orgs}
    assert {org_a, org_b} <= ids


def test_lijst_actieve_organisaties_negeert_inactieve_org(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Org A", slug="org-a", store_ids=[])
    with engine.begin() as conn:
        conn.execute(organisaties.update().where(organisaties.c.id == org_id).values(actief=False))

    orgs = lijst_actieve_organisaties(engine)

    assert org_id not in {o.id for o in orgs}
