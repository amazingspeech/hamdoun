"""Fase 5 NODIG 1 (herbestel-advies): per-organisatie instellingen die niet
uit het modelartefact of een koppeling komen, maar door de winkelier zelf
worden opgegeven — momenteel alleen de gemiddelde omzet per verkocht stuk,
nodig om een omzetvoorspelling om te rekenen naar een stuks-schatting."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine

from db.schema import organisaties


def stel_gemiddelde_omzet_per_stuk_in(engine: Engine, organisatie_id: int, bedrag: float) -> None:
    with engine.begin() as conn:
        conn.execute(
            organisaties.update()
            .where(organisaties.c.id == organisatie_id)
            .values(gemiddelde_omzet_per_stuk=bedrag)
        )


def haal_gemiddelde_omzet_per_stuk(engine: Engine, organisatie_id: int) -> Optional[float]:
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.gemiddelde_omzet_per_stuk).where(organisaties.c.id == organisatie_id)
        ).scalar_one_or_none()


def _stel_stripe_koppeling_in_op_connectie(
    conn: Connection, organisatie_id: int, stripe_customer_id: str, stripe_subscription_id: str
) -> None:
    conn.execute(
        organisaties.update()
        .where(organisaties.c.id == organisatie_id)
        .values(stripe_customer_id=stripe_customer_id, stripe_subscription_id=stripe_subscription_id)
    )


def lijst_actieve_organisaties(engine: Engine):
    """Voor de wekelijkse herbestel-mail (Fase 5 NODIG 3), die elke actieve
    organisatie langsloopt om te bepalen of er iets te melden valt."""
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.id, organisaties.c.naam).where(organisaties.c.actief.is_(True))
        ).all()


def stel_stripe_koppeling_in(
    engine: Engine, organisatie_id: int, stripe_customer_id: str, stripe_subscription_id: str,
    conn: Optional[Connection] = None,
) -> None:
    """Fase 5 NODIG 5: gezet door de webhook-handler (serving/app.py) zodra
    een self-serve aanmelding voltooid is — nodig als referentie voor
    toekomstig gebruik (opzeggen, factuurgeschiedenis tonen), niet voor
    toegangscontrole zelf (die blijft puur op organisatie_id lopen).

    conn: optioneel een al-openstaande connectie/transactie, zie
    db.bootstrap.bootstrap_organisatie voor dezelfde reden/patroon."""
    if conn is not None:
        _stel_stripe_koppeling_in_op_connectie(conn, organisatie_id, stripe_customer_id, stripe_subscription_id)
        return
    with engine.begin() as eigen_conn:
        _stel_stripe_koppeling_in_op_connectie(eigen_conn, organisatie_id, stripe_customer_id, stripe_subscription_id)
