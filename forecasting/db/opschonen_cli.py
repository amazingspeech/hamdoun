"""Fase 4 (AVG-vereiste, zie FASE4-SAAS-FOUNDATION.md beslissing 9):
dagelijkse cron-invocatie die organisaties definitief verwijdert 30 dagen
na deactivering (zie db.organisaties.verwijder_organisatie). Leest alleen
TENANTS_DB_PAD rechtstreeks uit de omgeving (zelfde default als
serving.config.laad_settings) in plaats van de volledige
serving-configuratie te laden — dit script raakt nooit het modelartefact
of api_keys.json, en hoeft dus niet aan MODEL_VERSION/API_KEYS_FILE
gebonden te zijn zoals serving.herbestel_email_cli dat wel is. Zie
deploy/DEPLOY.md voor de cron-regel.

Gebruik: python3 -m db.opschonen_cli
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from db.organisaties import haal_te_verwijderen_organisaties, verwijder_organisatie
from db.schema import maak_database


def main() -> list[int]:
    load_dotenv()
    tenants_db_pad = Path(os.environ.get("TENANTS_DB_PAD", "tenants.db"))
    # Fail hard i.p.v. maak_database() stilzwijgend een nieuwe, lege database
    # laten aanmaken (zelfde "fail hard on missing required config"-patroon
    # als serving/config.py's API_KEYS_FILE-check) — dit script is een AVG-
    # nalevingscontrole, en een misconfigureerde TENANTS_DB_PAD zou anders
    # elke nacht "0 organisatie(s) verwijderd" rapporteren, ononderscheidbaar
    # van een correct geconfigureerde, lege wachtrij.
    if not tenants_db_pad.exists():
        raise RuntimeError(
            f"TENANTS_DB_PAD ({tenants_db_pad}) bestaat niet. Dit script maakt "
            "nooit stilzwijgend een nieuwe, lege database aan — controleer of "
            "TENANTS_DB_PAD in de omgeving naar de juiste, bestaande database wijst."
        )
    engine = maak_database(tenants_db_pad)

    nu = datetime.now(timezone.utc)
    te_verwijderen = haal_te_verwijderen_organisaties(engine, nu)

    verwijderd: list[int] = []
    for organisatie_id in te_verwijderen:
        try:
            verwijder_organisatie(engine, organisatie_id)
        except Exception as e:
            # Alleen het exceptietype loggen, nooit str(e): een toekomstige
            # wijziging in verwijder_organisatie() of een onverwacht
            # exception-type zou anders PII (naam/e-mail) in de foutmelding
            # kunnen laten lekken. Dit is een structurele garantie, geen
            # aanname over de huidige foutinhoud.
            print(f"FOUT bij verwijderen van organisatie {organisatie_id}: {type(e).__name__}")
            continue
        verwijderd.append(organisatie_id)
        print(f"organisatie {organisatie_id} verwijderd op {nu.isoformat()}")

    print(
        f"{len(verwijderd)} organisatie(s) verwijderd uit {tenants_db_pad}: "
        f"{verwijderd if verwijderd else '(geen)'}"
    )
    return verwijderd


if __name__ == "__main__":
    main()
