"""Fase 5 NODIG 3: wekelijkse cron-invocatie (maandagochtend) van de
herbestel-mail. Gebruikt dezelfde omgevingsvariabelen als serving.app
(MODEL_VERSION, MODELS_DIR, TENANTS_DB_PAD, MAIL_*) — geen aparte
argparse-configuratie, want dit draait in dezelfde omgeving als de
serving-laag zelf (zie deploy/DEPLOY.md voor de cron-regel).

Gebruik: python3 -m serving.herbestel_email_cli
"""
from __future__ import annotations

from datetime import date

from dotenv import load_dotenv

from db.schema import maak_database
from serving.config import laad_settings
from serving.herbestel_email import verstuur_wekelijkse_herbestel_mails
from training.artifact import laad_artefact


def main() -> list[str]:
    load_dotenv()
    settings = laad_settings()
    artefact = laad_artefact(settings.models_dir, settings.model_version, versleuteld=settings.encrypt_at_rest)
    engine = maak_database(settings.tenants_db_pad)

    mail_config = {
        "smtp_host": settings.mail_smtp_host,
        "smtp_poort": settings.mail_smtp_poort,
        "afzender": settings.mail_afzender,
        "smtp_gebruiker": settings.mail_smtp_gebruiker,
        "smtp_wachtwoord": settings.mail_smtp_wachtwoord,
    }
    verstuurd = verstuur_wekelijkse_herbestel_mails(
        engine, modellen=artefact["modellen"], historie=artefact["historie"],
        winkel_metadata=artefact["winkel_metadata"], mail_config=mail_config, start_datum=date.today(),
    )
    print(f"{len(verstuurd)} herbestel-mail(s) verstuurd: {', '.join(verstuurd) if verstuurd else '(geen)'}")
    return verstuurd


if __name__ == "__main__":
    main()
