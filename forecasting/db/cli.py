"""Command-line entry point voor Stap 0: database aanmaken en één
bootstrap-organisatie koppelen aan alle store-ID's uit een modelartefact.

Gebruik: python3 -m db.cli --models-dir models --model-version <versie> \
    --organisatie-naam "Bestaande klant" --organisatie-slug bestaande-klant
"""
from __future__ import annotations

import argparse
from pathlib import Path

from db.bootstrap import bootstrap_organisatie
from db.schema import maak_database
from training.artifact import laad_artefact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--database-pad", type=Path, default=Path("tenants.db"))
    parser.add_argument("--organisatie-naam", required=True)
    parser.add_argument("--organisatie-slug", required=True)
    parser.add_argument("--encrypt", action="store_true")
    args = parser.parse_args(argv)

    artefact = laad_artefact(args.models_dir, args.model_version, versleuteld=args.encrypt)
    store_ids = sorted(int(s) for s in artefact["winkel_metadata"]["Store"].unique())

    engine = maak_database(args.database_pad)
    org_id = bootstrap_organisatie(
        engine, naam=args.organisatie_naam, slug=args.organisatie_slug, store_ids=store_ids
    )

    print(f"Organisatie aangemaakt: id={org_id}, {len(store_ids)} winkels gekoppeld.")
    return org_id


if __name__ == "__main__":
    main()
