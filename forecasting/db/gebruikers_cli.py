"""Command-line entry point voor Stap 3: handmatig een gebruiker aanmaken
voor een organisatie. Geen self-service-registratie (beslissing 1,
FASE4-SAAS-FOUNDATION.md) — dit is de enige manier om een account aan te
maken.

Gebruik: python3 -m db.gebruikers_cli --database-pad tenants.db \
    --organisatie-slug bestaande-klant --email naam@klant.nl --wachtwoord ...
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import select

from db.gebruikers import maak_gebruiker
from db.schema import maak_database, organisaties


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-pad", type=Path, required=True)
    parser.add_argument("--organisatie-slug", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--wachtwoord", required=True)
    parser.add_argument("--rol", default="lid")
    args = parser.parse_args(argv)

    engine = maak_database(args.database_pad)
    with engine.connect() as conn:
        org_rij = conn.execute(
            select(organisaties).where(organisaties.c.slug == args.organisatie_slug)
        ).one_or_none()
    if org_rij is None:
        raise RuntimeError(f"Organisatie met slug '{args.organisatie_slug}' bestaat niet.")

    gebruiker_id = maak_gebruiker(
        engine, organisatie_id=org_rij.id, email=args.email, wachtwoord=args.wachtwoord, rol=args.rol
    )
    print(f"Gebruiker aangemaakt: id={gebruiker_id}, email={args.email}, organisatie='{args.organisatie_slug}'.")
    return gebruiker_id


if __name__ == "__main__":
    main()
