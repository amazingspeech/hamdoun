from db.aanmeldingen import (
    genereer_unieke_organisatie_slug,
    haal_aanmelding_bij_sessie,
    maak_aanmelding,
    voltooi_aanmelding,
)
from db.bootstrap import bootstrap_organisatie
from db.schema import maak_database


def _maak_aanmelding(engine, sessie_id="cs_test_123"):
    return maak_aanmelding(
        engine,
        organisatie_naam="Bakkerij De Vries",
        organisatie_slug="bakkerij-de-vries",
        email="devries@voorbeeld.nl",
        wachtwoord_hash="x",
        wachtwoord_salt="y",
        stripe_checkout_session_id=sessie_id,
    )


def test_maak_aanmelding_is_nog_niet_voltooid(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    aanmelding_id = _maak_aanmelding(engine)

    rij = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    assert rij.id == aanmelding_id
    assert rij.organisatie_id is None
    assert rij.voltooid_op is None


def test_haal_aanmelding_bij_sessie_onbekende_sessie_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    assert haal_aanmelding_bij_sessie(engine, "cs_bestaat_niet") is None


def test_voltooi_aanmelding_koppelt_organisatie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    aanmelding_id = _maak_aanmelding(engine)
    org_id = bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[])

    voltooi_aanmelding(engine, aanmelding_id=aanmelding_id, organisatie_id=org_id)

    rij = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    assert rij.organisatie_id == org_id
    assert rij.voltooid_op is not None


def test_webhook_kan_veilig_tweemaal_dezelfde_sessie_verwerken(tmp_path):
    """Stripe kan hetzelfde event meermaals afleveren — de webhook-handler
    moet aan organisatie_id kunnen zien dat een aanmelding al voltooid is,
    zonder een tweede keer een organisatie aan te maken."""
    engine = maak_database(tmp_path / "tenants.db")
    aanmelding_id = _maak_aanmelding(engine)
    org_id = bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[])
    voltooi_aanmelding(engine, aanmelding_id=aanmelding_id, organisatie_id=org_id)

    rij = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    assert rij.organisatie_id is not None  # de webhook-handler leest dit als "al verwerkt"


def test_genereer_unieke_organisatie_slug_basisgeval(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    assert genereer_unieke_organisatie_slug(engine, "Bakkerij De Vries") == "bakkerij-de-vries"


def test_genereer_unieke_organisatie_slug_normaliseert_leestekens_en_spaties(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    assert genereer_unieke_organisatie_slug(engine, "  Café 't Hoekje!!  ") == "cafe-t-hoekje"


def test_genereer_unieke_organisatie_slug_wijkt_uit_bij_bestaande_organisatie(tmp_path):
    """Twee klanten kunnen dezelfde bedrijfsnaam gebruiken (bv. twee losse
    'Bakker Jansen'-zaken) — de slug moet dan alsnog uniek worden, niet
    stuklopen op de unique constraint in db.schema.organisaties."""
    engine = maak_database(tmp_path / "tenants.db")
    bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[])

    assert genereer_unieke_organisatie_slug(engine, "Bakkerij De Vries") == "bakkerij-de-vries-2"


def test_genereer_unieke_organisatie_slug_wijkt_uit_bij_openstaande_aanmelding(tmp_path):
    """Ook een nog-niet-voltooide aanmelding (iemand die de Stripe Checkout-
    pagina nog niet heeft afgerond) telt mee — anders zou een tweede
    aanmelding met dezelfde naam pas bij de webhook (na de betaling) op de
    unique constraint stuklopen."""
    engine = maak_database(tmp_path / "tenants.db")
    maak_aanmelding(
        engine, organisatie_naam="Bakkerij De Vries", organisatie_slug="bakkerij-de-vries",
        email="eerste@voorbeeld.nl", wachtwoord_hash="x", wachtwoord_salt="y",
        stripe_checkout_session_id="cs_test_eerste",
    )

    assert genereer_unieke_organisatie_slug(engine, "Bakkerij De Vries") == "bakkerij-de-vries-2"
