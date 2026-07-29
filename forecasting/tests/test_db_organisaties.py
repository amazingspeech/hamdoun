from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from db.bootstrap import bootstrap_organisatie
from db.organisaties import (
    deactiveer_organisatie,
    haal_gemiddelde_omzet_per_stuk,
    haal_ingekochte_leden,
    haal_ingekochte_winkels,
    haal_organisatie_id_bij_stripe_subscription,
    haal_te_verwijderen_organisaties,
    haal_trial_verloopt_op,
    is_actief,
    is_in_proefperiode,
    kvk_nummer_heeft_organisatie,
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


def test_nieuwe_organisatie_is_actief(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    assert is_actief(engine, organisatie_id=org_id) is True


def test_deactiveer_organisatie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    deactiveer_organisatie(engine, organisatie_id=org_id)

    assert is_actief(engine, organisatie_id=org_id) is False


def test_is_actief_onbekende_organisatie_geeft_false(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    assert is_actief(engine, organisatie_id=999) is False


def test_haal_organisatie_id_bij_stripe_subscription(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    stel_stripe_koppeling_in(engine, organisatie_id=org_id, stripe_customer_id="cus_123", stripe_subscription_id="sub_456")

    assert haal_organisatie_id_bij_stripe_subscription(engine, "sub_456") == org_id


def test_haal_organisatie_id_bij_onbekend_stripe_subscription_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    assert haal_organisatie_id_bij_stripe_subscription(engine, "sub_onbekend") is None


def test_handmatig_aangemaakte_organisatie_is_niet_in_proefperiode(tmp_path):
    """bootstrap_organisatie zet trial_verloopt_op nooit — een handmatig
    onboarde klant (bv. via db/cli.py) is per ontwerp nooit trial-beperkt."""
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    assert is_in_proefperiode(engine, organisatie_id=org_id) is False


def test_organisatie_met_toekomstige_trial_verloopt_op_is_in_proefperiode(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    toekomst = datetime.now(timezone.utc) + timedelta(days=14)
    with engine.begin() as conn:
        conn.execute(organisaties.update().where(organisaties.c.id == org_id).values(trial_verloopt_op=toekomst))

    assert is_in_proefperiode(engine, organisatie_id=org_id) is True


def test_organisatie_met_verlopen_trial_verloopt_op_is_niet_meer_in_proefperiode(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    verleden = datetime.now(timezone.utc) - timedelta(days=1)
    with engine.begin() as conn:
        conn.execute(organisaties.update().where(organisaties.c.id == org_id).values(trial_verloopt_op=verleden))

    assert is_in_proefperiode(engine, organisatie_id=org_id) is False


def test_haal_trial_verloopt_op_zonder_proefperiode_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    assert haal_trial_verloopt_op(engine, organisatie_id=org_id) is None


def test_haal_trial_verloopt_op_geeft_ingestelde_waarde_terug(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    verloopt_op = datetime.now(timezone.utc) + timedelta(days=14)
    with engine.begin() as conn:
        conn.execute(organisaties.update().where(organisaties.c.id == org_id).values(trial_verloopt_op=verloopt_op))

    assert haal_trial_verloopt_op(engine, organisatie_id=org_id) == verloopt_op.replace(tzinfo=None)


def test_kvk_nummer_heeft_organisatie_onbekend_geeft_false(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    assert kvk_nummer_heeft_organisatie(engine, "12345678") is False


def test_kvk_nummer_heeft_organisatie_bekend_geeft_true(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[], kvk_nummer="12345678")
    assert kvk_nummer_heeft_organisatie(engine, "12345678") is True


def test_haal_ingekochte_leden_zonder_waarde_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Handmatige Klant", slug="handmatige-klant", store_ids=[])
    assert haal_ingekochte_leden(engine, org_id) is None


def test_haal_ingekochte_leden_met_waarde(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[], ingekochte_leden=3)
    assert haal_ingekochte_leden(engine, org_id) == 3


def test_haal_ingekochte_winkels_met_waarde(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[], ingekochte_winkels=2)
    assert haal_ingekochte_winkels(engine, org_id) == 2


def test_deactiveer_organisatie_zet_gedeactiveerd_op(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    voor = datetime.now(timezone.utc)
    deactiveer_organisatie(engine, organisatie_id=org_id)
    na = datetime.now(timezone.utc)

    with engine.connect() as conn:
        rij = conn.execute(select(organisaties.c.gedeactiveerd_op).where(organisaties.c.id == org_id)).one()
    gedeactiveerd_op = rij.gedeactiveerd_op.replace(tzinfo=timezone.utc)
    assert voor <= gedeactiveerd_op <= na


def test_haal_te_verwijderen_organisaties_negeert_nog_actieve_org(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    resultaat = haal_te_verwijderen_organisaties(engine, nu=datetime.now(timezone.utc))

    assert org_id not in resultaat


def test_haal_te_verwijderen_organisaties_negeert_net_gedeactiveerde_org(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    deactiveer_organisatie(engine, organisatie_id=org_id)

    resultaat = haal_te_verwijderen_organisaties(engine, nu=datetime.now(timezone.utc))

    assert org_id not in resultaat


def test_haal_te_verwijderen_organisaties_vindt_org_na_wachtperiode(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    deactiveer_organisatie(engine, organisatie_id=org_id)
    over_31_dagen = datetime.now(timezone.utc) + timedelta(days=31)

    resultaat = haal_te_verwijderen_organisaties(engine, nu=over_31_dagen)

    assert org_id in resultaat


def test_haal_te_verwijderen_organisaties_negeert_org_zonder_gedeactiveerd_op(tmp_path):
    """Kan na deze wijziging niet meer voorkomen via deactiveer_organisatie()
    zelf, maar defensief getest: een actief=False-rij zonder
    gedeactiveerd_op (bv. een oude rij van vóór deze wijziging) mag nooit
    een crash geven."""
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    with engine.begin() as conn:
        conn.execute(organisaties.update().where(organisaties.c.id == org_id).values(actief=False))
    over_31_dagen = datetime.now(timezone.utc) + timedelta(days=31)

    resultaat = haal_te_verwijderen_organisaties(engine, nu=over_31_dagen)

    assert org_id not in resultaat
