"""Command-line entry point voor Stap 1: alle keys uit een bestaande
api_keys.json overzetten naar de database, gekoppeld aan één organisatie
(op slug). Verandert api_keys.json zelf niet — de draaiende API blijft
die lezen totdat Stap 2 het uitleesmechanisme omzet.

Gebruik: python3 -m db.migreer_keys_cli --api-keys-json api_keys.json \
    --database-pad tenants.db --organisatie-slug bestaande-klant
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import select

from db.api_keys import migreer_bestaande_key
from db.schema import maak_database, organisaties
from security.api_keys import laad_keys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-keys-json", type=Path, required=True)
    parser.add_argument("--database-pad", type=Path, required=True)
    parser.add_argument("--organisatie-slug", required=True)
    args = parser.parse_args(argv)

    engine = maak_database(args.database_pad)
    with engine.connect() as conn:
        org_rij = conn.execute(
            select(organisaties).where(organisaties.c.slug == args.organisatie_slug)
        ).one_or_none()
    if org_rij is None:
        raise RuntimeError(f"Organisatie met slug '{args.organisatie_slug}' bestaat niet.")

    keys = laad_keys(args.api_keys_json)
    for naam, info in keys.items():
        migreer_bestaande_key(engine, organisatie_id=org_rij.id, naam=naam, hash=info["hash"], salt=info["salt"])

    print(f"{len(keys)} key(s) gemigreerd naar organisatie '{args.organisatie_slug}'.")
    return len(keys)


if __name__ == "__main__":
    main()
