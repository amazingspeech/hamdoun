from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from db.schema import (
    aanmeldingen,
    gebruiker_winkels,
    gebruikers,
    maak_database,
    organisaties,
    wachtwoord_reset_tokens,
    winkels,
)


def test_maak_database_maakt_organisaties_en_winkels_tabellen(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    tabellen = set(inspect(engine).get_table_names())
    assert {
        "organisaties", "winkels", "api_keys", "gebruikers", "sessies", "gebruiker_winkels",
        "wachtwoord_reset_tokens",
    } <= tabellen


def test_eigen_winkels_tabel_bestaat_met_verwachte_kolommen(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    inspector = inspect(engine)
    kolommen = {k["name"] for k in inspector.get_columns("eigen_winkels")}
    assert kolommen == {"id", "organisatie_id", "naam", "aangemaakt_op"}


def test_eigen_winkel_instellingen_tabel_bestaat_met_verwachte_kolommen(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    inspector = inspect(engine)
    kolommen = {k["name"] for k in inspector.get_columns("eigen_winkel_instellingen")}
    assert kolommen == {"eigen_winkel_id", "gemiddelde_omzet_per_stuk"}


def test_eigen_verkoopdata_is_gescoped_op_eigen_winkel_id(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    inspector = inspect(engine)
    kolommen = {k["name"] for k in inspector.get_columns("eigen_verkoopdata")}
    assert "eigen_winkel_id" in kolommen
    assert "organisatie_id" not in kolommen


def test_eigen_product_verkoopdata_is_gescoped_op_eigen_winkel_id(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    inspector = inspect(engine)
    kolommen = {k["name"] for k in inspector.get_columns("eigen_product_verkoopdata")}
    assert "eigen_winkel_id" in kolommen
    assert "organisatie_id" not in kolommen


def test_organisatie_gemiddelde_omzet_per_stuk_is_optioneel(tmp_path):
    """Nieuwe organisaties hebben nog geen herbestel-prijs ingesteld — dat
    mag nooit een verplicht veld zijn bij het aanmaken."""
    engine = maak_database(tmp_path / "tenants.db")
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        org_id = conn.execute(
            organisaties.insert().values(naam="Org A", slug="org-a", actief=True, aangemaakt_op=nu)
        ).inserted_primary_key[0]

    with engine.connect() as conn:
        rij = conn.execute(organisaties.select().where(organisaties.c.id == org_id)).one()
    assert rij.gemiddelde_omzet_per_stuk is None


def test_organisatie_gemiddelde_omzet_per_stuk_kan_ingesteld_worden(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        org_id = conn.execute(
            organisaties.insert().values(naam="Org A", slug="org-a", actief=True, aangemaakt_op=nu)
        ).inserted_primary_key[0]
        conn.execute(
            organisaties.update().where(organisaties.c.id == org_id).values(gemiddelde_omzet_per_stuk=12.5)
        )

    with engine.connect() as conn:
        rij = conn.execute(organisaties.select().where(organisaties.c.id == org_id)).one()
    assert rij.gemiddelde_omzet_per_stuk == 12.5


def test_reset_token_hash_moet_uniek_zijn(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        org_id = conn.execute(
            organisaties.insert().values(naam="Org A", slug="org-a", actief=True, aangemaakt_op=nu)
        ).inserted_primary_key[0]
        gebruiker_id = conn.execute(
            gebruikers.insert().values(
                organisatie_id=org_id, email="test@klant.nl", wachtwoord_hash="x", wachtwoord_salt="y",
                rol="eigenaar", actief=True, aangemaakt_op=nu,
            )
        ).inserted_primary_key[0]
        conn.execute(
            wachtwoord_reset_tokens.insert().values(
                gebruiker_id=gebruiker_id, token_hash="dezelfde-hash", aangemaakt_op=nu,
                verloopt_op=nu, gebruikt_op=None,
            )
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                wachtwoord_reset_tokens.insert().values(
                    gebruiker_id=gebruiker_id, token_hash="dezelfde-hash", aangemaakt_op=nu,
                    verloopt_op=nu, gebruikt_op=None,
                )
            )


def test_extern_store_id_moet_uniek_zijn(tmp_path):
    """Een winkel hoort in het huidige gedeelde-modelontwerp bij precies één
    organisatie (FASE4-SAAS-FOUNDATION.md, beslissing 4) — de database moet
    dat afdwingen, niet alleen applicatiecode."""
    engine = maak_database(tmp_path / "tenants.db")
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        org_id = conn.execute(
            organisaties.insert().values(naam="Org A", slug="org-a", actief=True, aangemaakt_op=nu)
        ).inserted_primary_key[0]
        conn.execute(
            winkels.insert().values(
                organisatie_id=org_id, extern_store_id=1, naam=None, actief=True, aangemaakt_op=nu
            )
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                winkels.insert().values(
                    organisatie_id=org_id, extern_store_id=1, naam=None, actief=True, aangemaakt_op=nu
                )
            )


def test_gebruiker_winkel_combinatie_moet_uniek_zijn(tmp_path):
    """Eén toewijzing per (gebruiker, winkel) — dubbel toewijzen mag geen
    stille tweede rij opleveren."""
    engine = maak_database(tmp_path / "tenants.db")
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        org_id = conn.execute(
            organisaties.insert().values(naam="Org A", slug="org-a", actief=True, aangemaakt_op=nu)
        ).inserted_primary_key[0]
        winkel_id = conn.execute(
            winkels.insert().values(
                organisatie_id=org_id, extern_store_id=1, naam=None, actief=True, aangemaakt_op=nu
            )
        ).inserted_primary_key[0]
        gebruiker_id = conn.execute(
            gebruikers.insert().values(
                organisatie_id=org_id, email="lid@test.nl", wachtwoord_hash="x", wachtwoord_salt="y",
                rol="lid", actief=True, aangemaakt_op=nu,
            )
        ).inserted_primary_key[0]
        conn.execute(
            gebruiker_winkels.insert().values(gebruiker_id=gebruiker_id, winkel_id=winkel_id, aangemaakt_op=nu)
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                gebruiker_winkels.insert().values(gebruiker_id=gebruiker_id, winkel_id=winkel_id, aangemaakt_op=nu)
            )


def test_organisatie_stripe_kolommen_zijn_optioneel(tmp_path):
    """Handmatig aangemaakte organisaties (bootstrap_organisatie, geen
    self-serve signup) hebben geen Stripe-koppeling — deze kolommen mogen
    nooit verplicht zijn bij het aanmaken."""
    engine = maak_database(tmp_path / "tenants.db")
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        org_id = conn.execute(
            organisaties.insert().values(naam="Org A", slug="org-a", actief=True, aangemaakt_op=nu)
        ).inserted_primary_key[0]

    with engine.connect() as conn:
        rij = conn.execute(organisaties.select().where(organisaties.c.id == org_id)).one()
    assert rij.stripe_customer_id is None
    assert rij.stripe_subscription_id is None


def test_organisatie_trial_verloopt_op_is_optioneel(tmp_path):
    """Handmatig aangemaakte organisaties (bootstrap_organisatie, geen
    self-serve signup) hebben geen proefperiode — ze zijn per ontwerp nooit
    trial-beperkt (zie db.organisaties.is_in_proefperiode), dus deze kolom
    moet nullable zijn, net als de Stripe-kolommen hierboven."""
    engine = maak_database(tmp_path / "tenants.db")
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        org_id = conn.execute(
            organisaties.insert().values(naam="Org A", slug="org-a", actief=True, aangemaakt_op=nu)
        ).inserted_primary_key[0]

    with engine.connect() as conn:
        rij = conn.execute(organisaties.select().where(organisaties.c.id == org_id)).one()
    assert rij.trial_verloopt_op is None


def test_aanmelding_kan_aangemaakt_worden_zonder_organisatie(tmp_path):
    """Een aanmelding bestaat vanaf het moment een Stripe Checkout Session
    wordt gestart, ruim vóórdat de betaling (en dus de organisatie) er is —
    organisatie_id moet dus nullable zijn."""
    engine = maak_database(tmp_path / "tenants.db")
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        aanmelding_id = conn.execute(
            aanmeldingen.insert().values(
                organisatie_naam="Bakkerij De Vries",
                organisatie_slug="bakkerij-de-vries",
                email="devries@voorbeeld.nl",
                wachtwoord_hash="x",
                wachtwoord_salt="y",
                stripe_checkout_session_id="cs_test_123",
                organisatie_id=None,
                voltooid_op=None,
                aangemaakt_op=nu,
            )
        ).inserted_primary_key[0]

    with engine.connect() as conn:
        rij = conn.execute(aanmeldingen.select().where(aanmeldingen.c.id == aanmelding_id)).one()
    assert rij.organisatie_id is None
    assert rij.voltooid_op is None


def test_stripe_checkout_session_id_moet_uniek_zijn_op_aanmeldingen(tmp_path):
    """Stripe kan hetzelfde webhook-event meermaals versturen — de webhook-
    handler herkent een al-verwerkte sessie via deze kolom, dus die moet
    uniek zijn."""
    engine = maak_database(tmp_path / "tenants.db")
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            aanmeldingen.insert().values(
                organisatie_naam="Bakkerij De Vries",
                organisatie_slug="bakkerij-de-vries",
                email="devries@voorbeeld.nl",
                wachtwoord_hash="x",
                wachtwoord_salt="y",
                stripe_checkout_session_id="cs_test_123",
                organisatie_id=None,
                voltooid_op=None,
                aangemaakt_op=nu,
            )
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                aanmeldingen.insert().values(
                    organisatie_naam="Andere Zaak",
                    organisatie_slug="andere-zaak",
                    email="ander@voorbeeld.nl",
                    wachtwoord_hash="x",
                    wachtwoord_salt="y",
                    stripe_checkout_session_id="cs_test_123",
                    organisatie_id=None,
                    voltooid_op=None,
                    aangemaakt_op=nu,
                )
            )


def test_maak_database_voegt_ontbrekende_kolom_toe_aan_bestaande_tabel(tmp_path):
    """create_all() maakt alleen ontbrekende tábellen aan, nooit
    ontbrekende kolommen op een tabel die al bestaat — dit is precies wat
    er gebeurt bij een al-lopende database van vóór een schemawijziging
    (bv. de lokale tenants.db van vóór kvk_nummer). Simuleert dat scenario
    door de organisaties-tabel handmatig zonder die kolom aan te maken,
    roept maak_database() nogmaals aan, en verwacht dat de kolom er dan
    wél is — zonder bestaande data te verliezen."""
    database_pad = tmp_path / "tenants.db"
    oud_engine = create_engine(f"sqlite:///{database_pad}")
    with oud_engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE organisaties ("
            "id INTEGER PRIMARY KEY, naam VARCHAR NOT NULL, slug VARCHAR NOT NULL UNIQUE, "
            "actief BOOLEAN NOT NULL, aangemaakt_op DATETIME NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO organisaties (naam, slug, actief, aangemaakt_op) "
            "VALUES ('Bestaande klant', 'bestaande-klant', 1, '2026-01-01 00:00:00')"
        ))
    oud_engine.dispose()

    engine = maak_database(database_pad)

    kolommen = {k["name"] for k in inspect(engine).get_columns("organisaties")}
    assert "kvk_nummer" in kolommen
    with engine.connect() as conn:
        rij = conn.execute(organisaties.select().where(organisaties.c.slug == "bestaande-klant")).one()
    assert rij.naam == "Bestaande klant"
    assert rij.kvk_nummer is None
