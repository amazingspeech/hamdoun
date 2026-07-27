"""Database-schema voor de SaaS-fundamentlaag (Fase 4, Stap 0):
organisaties en de koppeltabel die vastlegt welke winkel (store_id uit het
modelartefact) bij welke organisatie hoort. Geen impact op het bestaande
model-artefact-mechanisme (training/artifact.py) — deze laag komt ernaast
als toegangslaag, niet als vervanging.

SQLAlchemy Core (geen ORM): consistent met de bestaande stijl van platte
functies in security/api_keys.py. SQLite nu, met een portable schema-opzet
zodat een latere overstap naar Postgres een migratie is, geen herontwerp
(zie forecasting/FASE4-SAAS-FOUNDATION.md)."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

organisaties = Table(
    "organisaties",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("naam", String, nullable=False),
    Column("slug", String, nullable=False, unique=True),
    Column("actief", Boolean, nullable=False, default=True),
    Column("aangemaakt_op", DateTime, nullable=False),
    # Fase 5 NODIG 1 (herbestel-advies): een winkelier vult dit één keer
    # zelf in — er is nergens in dit systeem echte product-/inventarisdata
    # (het model voorspelt totale omzet, geen losse stuks), dus dit is de
    # enige eerlijke manier om een omzetvoorspelling om te rekenen naar een
    # aantal-stuks-schatting zonder een verzonnen prijs te gebruiken.
    # Optioneel: zonder ingevulde waarde toont het dashboard geen
    # stuks-advies, alleen het bestaande omzetgetal.
    Column("gemiddelde_omzet_per_stuk", Float, nullable=True),
)

winkels = Table(
    "winkels",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("organisatie_id", Integer, ForeignKey("organisaties.id"), nullable=False),
    # extern_store_id: het Store-ID uit het modelartefact (historie.parquet /
    # winkel_metadata.parquet). Uniek, want in het huidige, gedeelde-model-
    # ontwerp (zie FASE4-SAAS-FOUNDATION.md, beslissing 4) hoort een winkel
    # bij precies één organisatie.
    Column("extern_store_id", Integer, nullable=False, unique=True),
    Column("naam", String, nullable=True),
    Column("actief", Boolean, nullable=False, default=True),
    Column("aangemaakt_op", DateTime, nullable=False),
)

api_keys = Table(
    "api_keys",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("organisatie_id", Integer, ForeignKey("organisaties.id"), nullable=False),
    Column("naam", String, nullable=False),
    # hash/salt: exact dezelfde PBKDF2-HMAC-SHA256-waarden als
    # security/api_keys.py produceert — deze tabel hergebruikt die
    # hash-functies, verzint geen nieuw formaat.
    Column("hash", String, nullable=False),
    Column("salt", String, nullable=False),
    Column("verlopen_op", DateTime, nullable=True),
    Column("actief", Boolean, nullable=False, default=True),
    Column("aangemaakt_op", DateTime, nullable=False),
)

gebruikers = Table(
    "gebruikers",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("organisatie_id", Integer, ForeignKey("organisaties.id"), nullable=False),
    Column("email", String, nullable=False, unique=True),
    # wachtwoord_hash/salt: zelfde PBKDF2-HMAC-SHA256-aanpak als hierboven
    # bij api_keys — hergebruikt security.api_keys.hash_key()/verifieer_key(),
    # geen apart wachtwoord-hashformaat.
    Column("wachtwoord_hash", String, nullable=False),
    Column("wachtwoord_salt", String, nullable=False),
    # rol bestaat al (voor het datamodel uit FASE4-SAAS-FOUNDATION.md), maar
    # wordt nog nergens afgedwongen — rolonderscheid (eigenaar/lid) is Stap 5,
    # niet Stap 3. Elke gebruiker is nu functioneel gelijk.
    Column("rol", String, nullable=False, default="lid"),
    Column("actief", Boolean, nullable=False, default=True),
    Column("aangemaakt_op", DateTime, nullable=False),
)

gebruiker_winkels = Table(
    "gebruiker_winkels",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("gebruiker_id", Integer, ForeignKey("gebruikers.id"), nullable=False),
    Column("winkel_id", Integer, ForeignKey("winkels.id"), nullable=False),
    Column("aangemaakt_op", DateTime, nullable=False),
    # Alleen relevant voor rol="lid" (zie db/gebruiker_winkels.py) — een
    # eigenaar heeft altijd org-brede toegang en krijgt hier nooit rijen.
    UniqueConstraint("gebruiker_id", "winkel_id", name="uq_gebruiker_winkel"),
)

sessies = Table(
    "sessies",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("gebruiker_id", Integer, ForeignKey("gebruikers.id"), nullable=False),
    # token_hash: SHA-256, niet PBKDF2. Een sessietoken is zelf al een
    # willekeurige, hoge-entropie waarde (secrets.token_urlsafe) — het
    # PBKDF2-trage-hashen bestaat om laag-entropie geheimen (wachtwoorden,
    # API-keys die een mens kiest) tegen brute-force te beschermen; dat
    # probeert hier niemand te raden, dus een snelle hash volstaat.
    Column("token_hash", String, nullable=False, unique=True),
    Column("aangemaakt_op", DateTime, nullable=False),
    Column("verloopt_op", DateTime, nullable=False),
)


def _migreer_ontbrekende_kolommen(engine: Engine) -> None:
    """create_all() maakt alleen ontbrekende tábellen aan, nooit
    ontbrekende kolommen op een tabel die al bestaat — dus een al-lopende
    database van vóór een schemawijziging (bv. een nieuwe nullable kolom
    op organisaties) krijgt die kolom anders nooit. Voegt zulke kolommen
    alsnog toe via een simpele ALTER TABLE, wat SQLite voor het toevoegen
    van een kolom native ondersteunt. Dit is bewust geen vervanging voor
    een echte migratietool (Alembic) — zie de afweging in het
    projectplan (FASE4-SAAS-FOUNDATION.md) over wanneer dat wél nodig
    wordt; voor incidentele, losse nullable kolommen op deze schaal
    volstaat dit."""
    inspector = inspect(engine)
    bestaande_tabellen = set(inspector.get_table_names())
    for tabel in metadata.sorted_tables:
        if tabel.name not in bestaande_tabellen:
            continue
        bestaande_kolommen = {kol["name"] for kol in inspector.get_columns(tabel.name)}
        for kolom in tabel.columns:
            if kolom.name in bestaande_kolommen:
                continue
            kolomtype = kolom.type.compile(engine.dialect)
            with engine.begin() as conn:
                conn.execute(text(f'ALTER TABLE "{tabel.name}" ADD COLUMN "{kolom.name}" {kolomtype}'))


def maak_database(database_pad: Path) -> Engine:
    """Maakt (indien nog niet aanwezig) de database aan op database_pad en
    zorgt dat alle tabellen in dit schema bestaan. Idempotent: bestaande
    tabellen worden nooit overschreven of leeggemaakt. Voegt ook
    ontbrekende kolommen toe aan al bestaande tabellen, zie
    _migreer_ontbrekende_kolommen()."""
    engine = create_engine(f"sqlite:///{database_pad}")
    metadata.create_all(engine)
    _migreer_ontbrekende_kolommen(engine)
    return engine
