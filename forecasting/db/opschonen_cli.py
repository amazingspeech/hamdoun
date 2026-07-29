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
    engine = maak_database(tenants_db_pad)

    nu = datetime.now(timezone.utc)
    te_verwijderen = haal_te_verwijderen_organisaties(engine, nu)

    verwijderd: list[int] = []
    for organisatie_id in te_verwijderen:
        try:
            verwijder_organisatie(engine, organisatie_id)
        except Exception as e:
            print(f"FOUT bij verwijderen van organisatie {organisatie_id}: {e}")
            continue
        verwijderd.append(organisatie_id)
        print(f"organisatie {organisatie_id} verwijderd op {nu.isoformat()}")

    print(f"{len(verwijderd)} organisatie(s) verwijderd: {verwijderd if verwijderd else '(geen)'}")
    return verwijderd


if __name__ == "__main__":
    main()
