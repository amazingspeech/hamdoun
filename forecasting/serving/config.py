"""Configuratie voor de serving-laag: leest environment variables, faalt
hard bij ontbrekende verplichte waarden — nooit een stille default voor iets
dat veiligheids- of correctheidskritisch is."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model_version: str
    models_dir: Path
    api_keys_file: Path
    audit_log_file: Path
    cors_allowed_origins: list[str]
    encrypt_at_rest: bool
    rate_limit_per_minute: int
    expose_docs: bool
    tenants_db_pad: Path


def laad_settings() -> Settings:
    model_version = os.environ.get("MODEL_VERSION")
    if not model_version:
        raise RuntimeError(
            "MODEL_VERSION ontbreekt in de omgeving. Zet 'm expliciet op een "
            "gepromoveerde modelversie (map onder models/) — de server start "
            "nooit met een impliciet 'laatste' model."
        )

    models_dir = Path(os.environ.get("MODELS_DIR", "models"))

    api_keys_file = Path(os.environ.get("API_KEYS_FILE", "api_keys.json"))
    if not api_keys_file.exists():
        raise RuntimeError(
            f"API_KEYS_FILE ({api_keys_file}) bestaat niet. Voeg minimaal één "
            "key toe met security.api_keys.voeg_key_toe() voordat de server start."
        )

    audit_log_file = Path(os.environ.get("AUDIT_LOG_FILE", "audit.log"))

    ruwe_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    cors_allowed_origins = [o.strip() for o in ruwe_origins.split(",") if o.strip()]
    # Ontbrekende/lege config = expliciet geen enkele origin toegestaan.
    # Nooit een wildcard-fallback, ook niet impliciet.

    encrypt_at_rest = os.environ.get("FORECASTING_ENCRYPT_AT_REST", "false").lower() == "true"
    if encrypt_at_rest and not os.environ.get("FORECASTING_ENCRYPTIE_SLEUTEL"):
        raise RuntimeError(
            "FORECASTING_ENCRYPT_AT_REST staat aan, maar FORECASTING_ENCRYPTIE_SLEUTEL "
            "ontbreekt. Genereer een sleutel met: python3 -m security.encryptie genereer-sleutel"
        )

    rate_limit = int(os.environ.get("RATE_LIMIT_PER_MINUUT", "60"))

    # Standaard uit: /docs, /redoc en /openapi.json geven ongeauthenticeerd
    # het volledige API-schema prijs. Zelfde "ontbrekende config = dicht"
    # patroon als CORS hierboven — een publieke demo-deployment hoeft dit
    # nooit aan te zetten, alleen bewust voor intern/ontwikkelgebruik.
    expose_docs = os.environ.get("EXPOSE_API_DOCS", "false").lower() == "true"

    # Geen fail-hard-op-ontbrekend hier zoals bij API_KEYS_FILE: een
    # ontbrekend databasebestand wordt door db.schema.maak_database()
    # automatisch aangemaakt als lege database (geen organisaties/keys),
    # wat elke aanvraag laat 401'en — een luide, veilige faalstand, geen
    # stil beveiligingsgat.
    tenants_db_pad = Path(os.environ.get("TENANTS_DB_PAD", "tenants.db"))

    return Settings(
        model_version=model_version,
        models_dir=models_dir,
        api_keys_file=api_keys_file,
        audit_log_file=audit_log_file,
        cors_allowed_origins=cors_allowed_origins,
        encrypt_at_rest=encrypt_at_rest,
        rate_limit_per_minute=rate_limit,
        expose_docs=expose_docs,
        tenants_db_pad=tenants_db_pad,
    )
