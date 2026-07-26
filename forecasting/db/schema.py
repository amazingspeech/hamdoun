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
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
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


def maak_database(database_pad: Path) -> Engine:
    """Maakt (indien nog niet aanwezig) de database aan op database_pad en
    zorgt dat alle tabellen in dit schema bestaan. Idempotent: bestaande
    tabellen worden nooit overschreven of leeggemaakt."""
    engine = create_engine(f"sqlite:///{database_pad}")
    metadata.create_all(engine)
    return engine
