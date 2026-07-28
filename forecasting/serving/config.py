"""Configuratie voor de serving-laag: leest environment variables, faalt
hard bij ontbrekende verplichte waarden — nooit een stille default voor iets
dat veiligheids- of correctheidskritisch is."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
    sessie_cookie_secure: bool
    # Mail is optioneel: nog geen endpoint hangt hier vandaag van af (dat
    # komt met wachtwoord-reset / herbestel-meldingen), dus dit faalt
    # bewust niet hard bij afwezigheid zoals MODEL_VERSION dat wel doet —
    # de aanroeper die mail daadwerkelijk gebruikt controleert zelf op
    # None, zie security/mail.py.
    mail_smtp_host: Optional[str] = None
    mail_smtp_poort: Optional[int] = None
    mail_afzender: Optional[str] = None
    mail_smtp_gebruiker: Optional[str] = None
    mail_smtp_wachtwoord: Optional[str] = None
    # Stripe is optioneel om dezelfde reden als mail hierboven: /signup en
    # /webhooks/stripe controleren zelf op None (zie serving/app.py) in
    # plaats van dat dit hier hard faalt — een deployment zonder self-serve
    # signup (bv. alleen handmatige onboarding) hoeft dit nooit te zetten.
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_id: Optional[str] = None
    stripe_price_id_extra_lid: Optional[str] = None
    stripe_price_id_extra_winkel: Optional[str] = None
    # Basis-URL van de draaiende app, nodig om Stripe Checkout's
    # success_url/cancel_url naar de juiste plek te laten wijzen (Stripe kan
    # dit niet zelf afleiden uit het inkomende verzoek).
    app_basis_url: Optional[str] = None
    # Fase "tier omhoog" onboarding: welk store_id uit het gedeelde
    # modelartefact als publiek, niet-tenant-gebonden voorbeeld dient voor
    # GET /voorbeeld/forecast (zie serving/app.py) — een self-serve
    # organisatie heeft nooit een eigen winkelbinding (zie
    # FASE4-SAAS-FOUNDATION.md beslissing 4), dus zonder dit voorbeeld ziet
    # zo'n organisatie wekenlang nooit een werkende voorspelling. Optioneel:
    # zonder ingesteld voorbeeld geeft dat endpoint een nette 503, geen crash.
    voorbeeld_store_id: Optional[int] = None


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

    # Standaard aan: sessiecookies horen nooit onversleuteld over http te
    # gaan. Alleen expliciet uitzetten voor lokale ontwikkeling zonder TLS
    # (zelfde "expliciete opt-out" patroon als hierboven, maar dan
    # omgekeerd — hier is de veilige default WEL aan).
    sessie_cookie_secure = os.environ.get("SESSIE_COOKIE_SECURE", "true").lower() == "true"

    mail_smtp_poort_ruw = os.environ.get("MAIL_SMTP_POORT")
    mail_smtp_poort = int(mail_smtp_poort_ruw) if mail_smtp_poort_ruw else None

    ruwe_voorbeeld_store_id = os.environ.get("VOORBEELD_STORE_ID")
    voorbeeld_store_id = int(ruwe_voorbeeld_store_id) if ruwe_voorbeeld_store_id else None

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
        sessie_cookie_secure=sessie_cookie_secure,
        mail_smtp_host=os.environ.get("MAIL_SMTP_HOST"),
        mail_smtp_poort=mail_smtp_poort,
        mail_afzender=os.environ.get("MAIL_AFZENDER"),
        mail_smtp_gebruiker=os.environ.get("MAIL_SMTP_GEBRUIKER"),
        mail_smtp_wachtwoord=os.environ.get("MAIL_SMTP_WACHTWOORD"),
        stripe_secret_key=os.environ.get("STRIPE_SECRET_KEY"),
        stripe_webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET"),
        stripe_price_id=os.environ.get("STRIPE_PRICE_ID"),
        stripe_price_id_extra_lid=os.environ.get("STRIPE_PRICE_ID_EXTRA_LID"),
        stripe_price_id_extra_winkel=os.environ.get("STRIPE_PRICE_ID_EXTRA_WINKEL"),
        app_basis_url=os.environ.get("APP_BASIS_URL"),
        voorbeeld_store_id=voorbeeld_store_id,
    )
