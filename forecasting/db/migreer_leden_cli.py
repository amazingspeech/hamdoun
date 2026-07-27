"""Command-line entry point voor de eenmalige migratie bij invoering van
rolgebaseerde winkeltoegang (portfolio-dashboard item 10): elk bestaand
lid krijgt een toewijzing voor alle winkels die nu al bij hun organisatie
horen, zodat niemand op het moment van deploy toegang verliest.

Gebruik: python3 -m db.migreer_leden_cli --database-pad tenants.db
"""
from __future__ import annotations

import argparse
from pathlib import Path

from db.gebruiker_winkels import migreer_bestaande_leden
from db.schema import maak_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-pad", type=Path, required=True)
    args = parser.parse_args(argv)

    engine = maak_database(args.database_pad)
    aantal = migreer_bestaande_leden(engine)

    print(f"{aantal} lid(leden) gemigreerd naar volledige winkeltoegang.")
    return aantal


if __name__ == "__main__":
    main()
