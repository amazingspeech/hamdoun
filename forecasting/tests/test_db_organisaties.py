from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from db.aanmeldingen import maak_aanmelding, voltooi_aanmelding
from db.api_keys import maak_api_key
from db.bootstrap import bootstrap_organisatie
from db.gebruiker_winkels import stel_toewijzingen_in
from db.gebruikers import maak_gebruiker
from db.organisaties import (
    deactiveer_organisatie,
    haal_ingekochte_leden,
    haal_ingekochte_winkels,
    haal_organisatie_id_bij_stripe_subscription,
    haal_te_verwijderen_organisaties,
    haal_trial_verloopt_op,
    heractiveer_organisatie,
    is_actief,
    is_in_proefperiode,
    kvk_nummer_heeft_organisatie,
    lijst_actieve_organisaties,
    stel_stripe_koppeling_in,
    verwijder_organisatie,
)
from db.product_verkoopdata import vervang_product_verkoopdata
from db.schema import (
    aanmeldingen,
    api_keys,
    eigen_product_verkoopdata,
    eigen_verkoopdata,
    gebruiker_winkels,
    gebruikers,
    maak_database,
    organisaties,
    sessies,
    wachtwoord_reset_tokens,
    winkels,
)
from db.sessies import maak_sessie
from db.verkoopdata import vervang_verkoopdata
from db.wachtwoord_reset import maak_reset_token


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


def test_heractiveer_organisatie_zet_actief_en_wist_gedeactiveerd_op(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    deactiveer_organisatie(engine, organisatie_id=org_id)

    heractiveer_organisatie(engine, organisatie_id=org_id)

    assert is_actief(engine, organisatie_id=org_id) is True
    with engine.connect() as conn:
        rij = conn.execute(select(organisaties.c.gedeactiveerd_op).where(organisaties.c.id == org_id)).one()
    assert rij.gedeactiveerd_op is None


def test_heractiveer_dan_opnieuw_deactiveren_geeft_verse_wachtperiode(tmp_path):
    """Regressietest voor de bug uit de finale review: zonder
    heractiveer_organisatie() (die gedeactiveerd_op expliciet terugzet naar
    None) zou een organisatie die handmatig gereactiveerd en later opnieuw
    gedeactiveerd wordt, meteen (met een stale oude gedeactiveerd_op) in
    aanmerking komen voor verwijdering — zonder enige nieuwe wachtperiode."""
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    deactiveer_organisatie(engine, organisatie_id=org_id)
    heractiveer_organisatie(engine, organisatie_id=org_id)
    deactiveer_organisatie(engine, organisatie_id=org_id)

    resultaat_meteen = haal_te_verwijderen_organisaties(engine, nu=datetime.now(timezone.utc))
    assert org_id not in resultaat_meteen

    over_31_dagen = datetime.now(timezone.utc) + timedelta(days=31)
    resultaat_na_wachtperiode = haal_te_verwijderen_organisaties(engine, nu=over_31_dagen)
    assert org_id in resultaat_na_wachtperiode


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


def test_verwijder_organisatie_verwijdert_alles(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[42])
    gebruiker_id = maak_gebruiker(
        engine, organisatie_id=org_id, email="eigenaar@klant.nl", wachtwoord="geheim123", rol="eigenaar"
    )
    maak_sessie(engine, gebruiker_id=gebruiker_id)
    maak_reset_token(engine, gebruiker_id=gebruiker_id)
    maak_api_key(engine, organisatie_id=org_id, naam="hoofdkey")
    stel_toewijzingen_in(engine, gebruiker_id=gebruiker_id, extern_store_ids=[42])
    vervang_verkoopdata(engine, organisatie_id=org_id, rijen=[("2026-01-01", 100.0)])
    vervang_product_verkoopdata(engine, organisatie_id=org_id, rijen=[("2026-01-01", "Brood", 10)])
    aanmelding_id = maak_aanmelding(
        engine, organisatie_naam="Klant", organisatie_slug="klant-aanmelding", email="eigenaar@klant.nl",
        wachtwoord_hash="hash", wachtwoord_salt="salt", stripe_checkout_session_id="cs_test_123",
        kvk_nummer="12345678", aantal_leden=1, aantal_winkels=1, was_kvk_herhaling=False,
    )
    voltooi_aanmelding(engine, aanmelding_id=aanmelding_id, organisatie_id=org_id)

    verwijder_organisatie(engine, organisatie_id=org_id)

    with engine.connect() as conn:
        assert conn.execute(select(organisaties).where(organisaties.c.id == org_id)).first() is None
        assert conn.execute(select(gebruikers).where(gebruikers.c.organisatie_id == org_id)).first() is None
        assert conn.execute(select(winkels).where(winkels.c.organisatie_id == org_id)).first() is None
        assert conn.execute(select(api_keys).where(api_keys.c.organisatie_id == org_id)).first() is None
        assert conn.execute(select(sessies).where(sessies.c.gebruiker_id == gebruiker_id)).first() is None
        assert conn.execute(
            select(wachtwoord_reset_tokens).where(wachtwoord_reset_tokens.c.gebruiker_id == gebruiker_id)
        ).first() is None
        assert conn.execute(
            select(gebruiker_winkels).where(gebruiker_winkels.c.gebruiker_id == gebruiker_id)
        ).first() is None
        assert conn.execute(select(eigen_verkoopdata).where(eigen_verkoopdata.c.organisatie_id == org_id)).first() is None
        assert conn.execute(
            select(eigen_product_verkoopdata).where(eigen_product_verkoopdata.c.organisatie_id == org_id)
        ).first() is None
        aanmelding_rij = conn.execute(select(aanmeldingen).where(aanmeldingen.c.id == aanmelding_id)).one()
    assert aanmelding_rij.organisatie_id is None


def test_verwijder_organisatie_laat_andere_organisatie_ongemoeid(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Org A", slug="org-a", store_ids=[1])
    org_b = bootstrap_organisatie(engine, naam="Org B", slug="org-b", store_ids=[2])
    gebruiker_b = maak_gebruiker(
        engine, organisatie_id=org_b, email="eigenaar@orgb.nl", wachtwoord="geheim123", rol="eigenaar"
    )
    maak_sessie(engine, gebruiker_id=gebruiker_b)
    maak_reset_token(engine, gebruiker_id=gebruiker_b)
    maak_api_key(engine, organisatie_id=org_b, naam="key-b")
    stel_toewijzingen_in(engine, gebruiker_id=gebruiker_b, extern_store_ids=[2])
    vervang_verkoopdata(engine, organisatie_id=org_b, rijen=[("2026-01-01", 50.0)])
    vervang_product_verkoopdata(engine, organisatie_id=org_b, rijen=[("2026-01-01", "Brood", 5)])
    aanmelding_b_id = maak_aanmelding(
        engine, organisatie_naam="Org B", organisatie_slug="org-b-aanmelding", email="eigenaar@orgb.nl",
        wachtwoord_hash="hash", wachtwoord_salt="salt", stripe_checkout_session_id="cs_test_orgb",
        kvk_nummer="87654321", aantal_leden=1, aantal_winkels=1, was_kvk_herhaling=False,
    )
    voltooi_aanmelding(engine, aanmelding_id=aanmelding_b_id, organisatie_id=org_b)

    verwijder_organisatie(engine, organisatie_id=org_a)

    with engine.connect() as conn:
        assert conn.execute(select(organisaties).where(organisaties.c.id == org_b)).first() is not None
        assert conn.execute(select(gebruikers).where(gebruikers.c.id == gebruiker_b)).first() is not None
        assert conn.execute(select(winkels).where(winkels.c.organisatie_id == org_b)).first() is not None
        assert conn.execute(select(api_keys).where(api_keys.c.organisatie_id == org_b)).first() is not None
        assert conn.execute(select(sessies).where(sessies.c.gebruiker_id == gebruiker_b)).first() is not None
        assert conn.execute(select(eigen_verkoopdata).where(eigen_verkoopdata.c.organisatie_id == org_b)).first() is not None
        assert conn.execute(
            select(wachtwoord_reset_tokens).where(wachtwoord_reset_tokens.c.gebruiker_id == gebruiker_b)
        ).first() is not None
        assert conn.execute(
            select(gebruiker_winkels).where(gebruiker_winkels.c.gebruiker_id == gebruiker_b)
        ).first() is not None
        assert conn.execute(
            select(eigen_product_verkoopdata).where(eigen_product_verkoopdata.c.organisatie_id == org_b)
        ).first() is not None
        aanmelding_b_rij = conn.execute(select(aanmeldingen).where(aanmeldingen.c.id == aanmelding_b_id)).one()
    assert aanmelding_b_rij.organisatie_id == org_b
