# Hard-delete Cascade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thirty days after an organization is deactivated (Stripe `customer.subscription.deleted`), a daily background job permanently deletes the organization and all its scoped data in one transaction, fulfilling the AVG/GDPR requirement flagged as open in `FASE4-SAAS-FOUNDATION.md` beslissing 9.

**Architecture:** A new `gedeactiveerd_op` timestamp column on `organisaties`, set whenever `deactiveer_organisatie()` runs. A `verwijder_organisatie()` function does the actual cascade delete — explicit SQLAlchemy Core deletes across every scoped table in one transaction, following the exact plain-function style already used throughout `db/`. A `db/opschonen_cli.py` cron entrypoint finds organizations past the 30-day grace period and calls `verwijder_organisatie()` on each.

**Tech Stack:** Python, SQLAlchemy Core (no ORM), SQLite, pytest (TDD), FastAPI (unaffected by this plan).

## Global Constraints

- Grace period: 30 days between deactivation and permanent deletion (spec: "Wachtperiode" decision).
- Cascade scope: `gebruikers`, `winkels`, `api_keys`, `sessies`, `wachtwoord_reset_tokens`, `gebruiker_winkels`, `eigen_verkoopdata`, `eigen_product_verkoopdata` are deleted; `aanmeldingen.organisatie_id` is set to `NULL` (row itself kept); the `organisaties` row itself is deleted entirely — no anonymized stub kept (spec: "Cascade-scope" and "Organisatie-rij" decisions).
- The audit log (`security/audit.py`) is explicitly out of scope — never touched by this plan (spec: "Audit-log" decision, and the spec's "Explicitly out of scope" section).
- No database-level `ON DELETE CASCADE` — explicit, plain SQLAlchemy Core functions only, matching every other function in `db/` (spec: "Cascade-aanpak" decision).
- The cron log (stdout, redirected to a logfile by cron) must log only `organisatie_id` and timestamp — never name, email, or any other field that is itself the data being deleted.
- No changes to the webhook handler's trigger condition or timing — only the addition of the `gedeactiveerd_op` timestamp when it already runs.

---

## File Structure

- `db/schema.py` (modify) — one new column, `organisaties.gedeactiveerd_op`.
- `db/organisaties.py` (modify) — `deactiveer_organisatie()` extended; two new functions, `verwijder_organisatie()` and `haal_te_verwijderen_organisaties()`.
- `db/opschonen_cli.py` (create) — the cron entrypoint.
- `tests/test_db_organisaties.py` (modify) — extended with tests for all three functions above.
- `tests/test_opschonen_cli.py` (create) — tests for the cron entrypoint.
- `deploy/DEPLOY.md` (modify) — new cron section, modeled on the existing weekly herbestel-mail section.

---

### Task 1: `gedeactiveerd_op` column + `deactiveer_organisatie()` timestamp

**Files:**
- Modify: `db/schema.py`
- Modify: `db/organisaties.py`
- Test: `tests/test_db_organisaties.py`

**Interfaces:**
- Produces: `organisaties.c.gedeactiveerd_op` (nullable DateTime column). `deactiveer_organisatie(engine, organisatie_id)` now also sets this column — consumed by Task 2's `haal_te_verwijderen_organisaties()`.

- [ ] **Step 1: Write the failing test**

In `tests/test_db_organisaties.py`, add to the existing imports:

```python
from datetime import datetime, timedelta, timezone
```

(This import already exists in the file exactly as `from datetime import datetime, timedelta, timezone` — no change needed there. Just confirm it's present.)

Add this test anywhere in the file:

```python
def test_deactiveer_organisatie_zet_gedeactiveerd_op(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    voor = datetime.now(timezone.utc)
    deactiveer_organisatie(engine, organisatie_id=org_id)
    na = datetime.now(timezone.utc)

    with engine.connect() as conn:
        rij = conn.execute(select(organisaties.c.gedeactiveerd_op).where(organisaties.c.id == org_id)).one()
    gedeactiveerd_op = rij.gedeactiveerd_op.replace(tzinfo=timezone.utc)
    assert voor <= gedeactiveerd_op <= na
```

- [ ] **Step 2: Run test to verify it fails**

Use the remote-Docker test pattern (local pytest is broken in this environment):

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_organisaties.py::test_deactiveer_organisatie_zet_gedeactiveerd_op -v'"
```

Run this in the foreground (or, if backgrounded, wait for it to actually finish before reading output — never assume completion from a partial read). Expected: FAIL — either an `AttributeError`/`KeyError` on `gedeactiveerd_op` (column doesn't exist yet) or the assertion fails because the column is `None`.

- [ ] **Step 3: Add the column to the schema**

In `db/schema.py`, in the `organisaties` table definition, add this after the existing `Column("ingekochte_winkels", Integer, nullable=True),` line (currently the last column before the closing `)`):

```python
    # Fase 4 hard-delete-cascade (AVG-vereiste, FASE4-SAAS-FOUNDATION.md
    # beslissing 9): tijdstip waarop deactiveer_organisatie() draaide.
    # NULL voor een nog-actieve organisatie. db.organisaties.
    # haal_te_verwijderen_organisaties() gebruikt dit om de wachtperiode
    # (30 dagen) te bepalen vóór definitieve verwijdering.
    Column("gedeactiveerd_op", DateTime, nullable=True),
```

- [ ] **Step 4: Extend `deactiveer_organisatie()` to set the new column**

In `db/organisaties.py`, replace:

```python
def deactiveer_organisatie(engine: Engine, organisatie_id: int) -> None:
    """Gezet door de webhook-handler zodra Stripe customer.subscription.
    deleted meldt (opzegging of einde van de betaalretry-cyclus) — zie
    serving/app.py. Alleen toegang intrekken, geen data verwijderen: een
    daadwerkelijke verwijdering (AVG-vereiste, beslissing 9 in
    FASE4-SAAS-FOUNDATION.md) is een aparte, bewust nog niet gebouwde
    stap — een geannuleerd abonnement kan nog binnen de betaalretry-cyclus
    alsnog herstellen, en onomkeerbaar verwijderen op basis van één
    webhook-event zou dat geen ruimte geven."""
    with engine.begin() as conn:
        conn.execute(organisaties.update().where(organisaties.c.id == organisatie_id).values(actief=False))
```

with:

```python
def deactiveer_organisatie(engine: Engine, organisatie_id: int) -> None:
    """Gezet door de webhook-handler zodra Stripe customer.subscription.
    deleted meldt (opzegging of einde van de betaalretry-cyclus) — zie
    serving/app.py. Zet ook gedeactiveerd_op, zodat db.opschonen_cli 30
    dagen later weet welke organisaties definitief verwijderd mogen
    worden (verwijder_organisatie() hieronder) — de daadwerkelijke
    verwijdering gebeurt hier nog niet: een geannuleerd abonnement kan
    nog binnen Stripe's eigen betaalretry-cyclus alsnog herstellen, en
    onomkeerbaar verwijderen op basis van één webhook-event zou daar geen
    ruimte voor geven."""
    with engine.begin() as conn:
        conn.execute(
            organisaties.update().where(organisaties.c.id == organisatie_id)
            .values(actief=False, gedeactiveerd_op=datetime.now(timezone.utc))
        )
```

- [ ] **Step 5: Run test to verify it passes**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_organisaties.py -v'"
```

Expected: PASS — the new test, and every existing test in this file (including `test_deactiveer_organisatie`, which only checks `is_actief()` and is unaffected by the new column).

- [ ] **Step 6: Commit**

```bash
git add db/schema.py db/organisaties.py tests/test_db_organisaties.py
git commit -m "feat: add gedeactiveerd_op timestamp on organization deactivation"
```

---

### Task 2: `haal_te_verwijderen_organisaties()` query helper

**Files:**
- Modify: `db/organisaties.py`
- Test: `tests/test_db_organisaties.py`

**Interfaces:**
- Consumes: `organisaties.c.gedeactiveerd_op` (Task 1).
- Produces: `haal_te_verwijderen_organisaties(engine: Engine, nu: datetime, wachtdagen: int = 30) -> list[int]` — consumed by Task 4's `db/opschonen_cli.py`.

- [ ] **Step 1: Write the failing tests**

Add these four tests to `tests/test_db_organisaties.py`:

```python
def test_haal_te_verwijderen_organisaties_negeert_nog_actieve_org(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    resultaat = haal_te_verwijderen_organisaties(engine, nu=datetime.now(timezone.utc))

    assert org_id not in resultaat


def test_haal_te_verwijderen_organisaties_negeert_net_gedeactiveerde_org(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    deactiveer_organisatie(engine, organisatie_id=org_id)

    resultaat = haal_te_verwijderen_organisaties(engine, nu=datetime.now(timezone.utc))

    assert org_id not in resultaat


def test_haal_te_verwijderen_organisaties_vindt_org_na_wachtperiode(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    deactiveer_organisatie(engine, organisatie_id=org_id)
    over_31_dagen = datetime.now(timezone.utc) + timedelta(days=31)

    resultaat = haal_te_verwijderen_organisaties(engine, nu=over_31_dagen)

    assert org_id in resultaat


def test_haal_te_verwijderen_organisaties_negeert_org_zonder_gedeactiveerd_op(tmp_path):
    """Kan na deze wijziging niet meer voorkomen via deactiveer_organisatie()
    zelf, maar defensief getest: een actief=False-rij zonder
    gedeactiveerd_op (bv. een oude rij van vóór deze wijziging) mag nooit
    een crash geven."""
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    with engine.begin() as conn:
        conn.execute(organisaties.update().where(organisaties.c.id == org_id).values(actief=False))
    over_31_dagen = datetime.now(timezone.utc) + timedelta(days=31)

    resultaat = haal_te_verwijderen_organisaties(engine, nu=over_31_dagen)

    assert org_id not in resultaat
```

Add `haal_te_verwijderen_organisaties` to the existing `from db.organisaties import (...)` block at the top of the file.

- [ ] **Step 2: Run tests to verify they fail**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_organisaties.py -k haal_te_verwijderen -v'"
```

Expected: FAIL with `ImportError: cannot import name 'haal_te_verwijderen_organisaties'`.

- [ ] **Step 3: Add `timedelta` to the imports in `db/organisaties.py`**

Change:

```python
from datetime import datetime, timezone
```

to:

```python
from datetime import datetime, timedelta, timezone
```

- [ ] **Step 4: Implement `haal_te_verwijderen_organisaties()`**

Add this function to `db/organisaties.py`, anywhere after `deactiveer_organisatie()`:

```python
def haal_te_verwijderen_organisaties(engine: Engine, nu: datetime, wachtdagen: int = 30) -> list[int]:
    """Voor db.opschonen_cli: welke organisaties zijn lang genoeg geleden
    gedeactiveerd om nu definitief verwijderd te mogen worden
    (verwijder_organisatie() hieronder). Los van die functie gehouden
    zodat de selectielogica (wíé komt in aanmerking) apart getest kan
    worden van de verwijdering zelf (wát er precies gebeurt als iemand
    verwijderd wordt)."""
    grens = nu - timedelta(days=wachtdagen)
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.id).where(
                organisaties.c.actief.is_(False),
                organisaties.c.gedeactiveerd_op.isnot(None),
                organisaties.c.gedeactiveerd_op < grens,
            )
        ).scalars().all()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_organisaties.py -v'"
```

Expected: PASS — all tests in the file.

- [ ] **Step 6: Commit**

```bash
git add db/organisaties.py tests/test_db_organisaties.py
git commit -m "feat: add haal_te_verwijderen_organisaties query helper"
```

---

### Task 3: `verwijder_organisatie()` cascade delete

**Files:**
- Modify: `db/organisaties.py`
- Test: `tests/test_db_organisaties.py`

**Interfaces:**
- Consumes: `db.gebruikers.maak_gebruiker(engine, organisatie_id, email, wachtwoord, rol="lid") -> int`; `db.sessies.maak_sessie(engine, gebruiker_id) -> str`; `db.wachtwoord_reset.maak_reset_token(engine, gebruiker_id) -> str`; `db.api_keys.maak_api_key(engine, organisatie_id, naam) -> tuple[int, str]`; `db.gebruiker_winkels.stel_toewijzingen_in(engine, gebruiker_id, extern_store_ids)`; `db.verkoopdata.vervang_verkoopdata(engine, organisatie_id, rijen: list[tuple[str, float]])`; `db.product_verkoopdata.vervang_product_verkoopdata(engine, organisatie_id, rijen: list[tuple[str, str, int]])`; `db.aanmeldingen.maak_aanmelding(engine, organisatie_naam, organisatie_slug, email, wachtwoord_hash, wachtwoord_salt, stripe_checkout_session_id, kvk_nummer, aantal_leden, aantal_winkels, was_kvk_herhaling) -> int`; `db.aanmeldingen.voltooi_aanmelding(engine, aanmelding_id, organisatie_id)`.
- Produces: `verwijder_organisatie(engine: Engine, organisatie_id: int) -> None` — consumed by Task 4's `db/opschonen_cli.py`.

- [ ] **Step 1: Write the failing tests**

Add these imports to the top of `tests/test_db_organisaties.py`, alongside the existing ones:

```python
from db.aanmeldingen import maak_aanmelding, voltooi_aanmelding
from db.api_keys import maak_api_key
from db.gebruiker_winkels import stel_toewijzingen_in
from db.gebruikers import maak_gebruiker
from db.organisaties import haal_te_verwijderen_organisaties, verwijder_organisatie
from db.product_verkoopdata import vervang_product_verkoopdata
from db.schema import (
    aanmeldingen,
    api_keys,
    eigen_product_verkoopdata,
    eigen_verkoopdata,
    gebruiker_winkels,
    gebruikers,
    maak_database,
    organisaties,
    sessies,
    wachtwoord_reset_tokens,
    winkels,
)
from db.sessies import maak_sessie
from db.verkoopdata import vervang_verkoopdata
from db.wachtwoord_reset import maak_reset_token
```

(Merge this with the existing `from db.schema import maak_database, organisaties` and `from db.organisaties import (...)` blocks — don't leave two separate import lines for the same module. Add `haal_te_verwijderen_organisaties` and `verwijder_organisatie` to the existing `db.organisaties` import block from Task 2, and expand the existing `db.schema` import block to include the new table names alongside `maak_database, organisaties`.)

Add these two tests:

```python
def test_verwijder_organisatie_verwijdert_alles(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[42])
    gebruiker_id = maak_gebruiker(
        engine, organisatie_id=org_id, email="eigenaar@klant.nl", wachtwoord="geheim123", rol="eigenaar"
    )
    maak_sessie(engine, gebruiker_id=gebruiker_id)
    maak_reset_token(engine, gebruiker_id=gebruiker_id)
    maak_api_key(engine, organisatie_id=org_id, naam="hoofdkey")
    stel_toewijzingen_in(engine, gebruiker_id=gebruiker_id, extern_store_ids=[42])
    vervang_verkoopdata(engine, organisatie_id=org_id, rijen=[("2026-01-01", 100.0)])
    vervang_product_verkoopdata(engine, organisatie_id=org_id, rijen=[("2026-01-01", "Brood", 10)])
    aanmelding_id = maak_aanmelding(
        engine, organisatie_naam="Klant", organisatie_slug="klant-aanmelding", email="eigenaar@klant.nl",
        wachtwoord_hash="hash", wachtwoord_salt="salt", stripe_checkout_session_id="cs_test_123",
        kvk_nummer="12345678", aantal_leden=1, aantal_winkels=1, was_kvk_herhaling=False,
    )
    voltooi_aanmelding(engine, aanmelding_id=aanmelding_id, organisatie_id=org_id)

    verwijder_organisatie(engine, organisatie_id=org_id)

    with engine.connect() as conn:
        assert conn.execute(select(organisaties).where(organisaties.c.id == org_id)).first() is None
        assert conn.execute(select(gebruikers).where(gebruikers.c.organisatie_id == org_id)).first() is None
        assert conn.execute(select(winkels).where(winkels.c.organisatie_id == org_id)).first() is None
        assert conn.execute(select(api_keys).where(api_keys.c.organisatie_id == org_id)).first() is None
        assert conn.execute(select(sessies).where(sessies.c.gebruiker_id == gebruiker_id)).first() is None
        assert conn.execute(
            select(wachtwoord_reset_tokens).where(wachtwoord_reset_tokens.c.gebruiker_id == gebruiker_id)
        ).first() is None
        assert conn.execute(
            select(gebruiker_winkels).where(gebruiker_winkels.c.gebruiker_id == gebruiker_id)
        ).first() is None
        assert conn.execute(select(eigen_verkoopdata).where(eigen_verkoopdata.c.organisatie_id == org_id)).first() is None
        assert conn.execute(
            select(eigen_product_verkoopdata).where(eigen_product_verkoopdata.c.organisatie_id == org_id)
        ).first() is None
        aanmelding_rij = conn.execute(select(aanmeldingen).where(aanmeldingen.c.id == aanmelding_id)).one()
    assert aanmelding_rij.organisatie_id is None


def test_verwijder_organisatie_laat_andere_organisatie_ongemoeid(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Org A", slug="org-a", store_ids=[1])
    org_b = bootstrap_organisatie(engine, naam="Org B", slug="org-b", store_ids=[2])
    gebruiker_b = maak_gebruiker(
        engine, organisatie_id=org_b, email="eigenaar@orgb.nl", wachtwoord="geheim123", rol="eigenaar"
    )
    maak_sessie(engine, gebruiker_id=gebruiker_b)
    maak_api_key(engine, organisatie_id=org_b, naam="key-b")
    vervang_verkoopdata(engine, organisatie_id=org_b, rijen=[("2026-01-01", 50.0)])

    verwijder_organisatie(engine, organisatie_id=org_a)

    with engine.connect() as conn:
        assert conn.execute(select(organisaties).where(organisaties.c.id == org_b)).first() is not None
        assert conn.execute(select(gebruikers).where(gebruikers.c.id == gebruiker_b)).first() is not None
        assert conn.execute(select(winkels).where(winkels.c.organisatie_id == org_b)).first() is not None
        assert conn.execute(select(api_keys).where(api_keys.c.organisatie_id == org_b)).first() is not None
        assert conn.execute(select(sessies).where(sessies.c.gebruiker_id == gebruiker_b)).first() is not None
        assert conn.execute(select(eigen_verkoopdata).where(eigen_verkoopdata.c.organisatie_id == org_b)).first() is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_organisaties.py -k verwijder_organisatie -v'"
```

Expected: FAIL with `ImportError: cannot import name 'verwijder_organisatie'`.

- [ ] **Step 3: Add the new table imports to `db/organisaties.py`**

Change:

```python
from db.schema import organisaties
```

to:

```python
from db.schema import (
    aanmeldingen,
    api_keys,
    eigen_product_verkoopdata,
    eigen_verkoopdata,
    gebruiker_winkels,
    gebruikers,
    organisaties,
    sessies,
    wachtwoord_reset_tokens,
    winkels,
)
```

- [ ] **Step 4: Implement `verwijder_organisatie()`**

Add this function to `db/organisaties.py`, after `haal_te_verwijderen_organisaties()`:

```python
def verwijder_organisatie(engine: Engine, organisatie_id: int) -> None:
    """Definitieve, onomkeerbare verwijdering (AVG-vereiste, beslissing 9
    in FASE4-SAAS-FOUNDATION.md) — aangeroepen door db.opschonen_cli, 30
    dagen na deactiveer_organisatie(). Eén transactie: alle betrokken
    tabellen worden leeggemaakt vóór de organisaties-rij zelf verdwijnt,
    zodat er nooit een tussentoestand met wees-rijen op schijf staat.
    aanmeldingen blijft als historisch aanmeld-record bestaan (het bevat
    op zichzelf geen persoonsgegevens meer zodra gebruikers/organisaties
    weg zijn), alleen de FK-verwijzing wordt losgekoppeld. De audit-log
    (security/audit.py) blijft bewust buiten dit bereik — zie de
    designspec voor de reden."""
    with engine.begin() as conn:
        gebruiker_ids = select(gebruikers.c.id).where(gebruikers.c.organisatie_id == organisatie_id)
        winkel_ids = select(winkels.c.id).where(winkels.c.organisatie_id == organisatie_id)

        conn.execute(sessies.delete().where(sessies.c.gebruiker_id.in_(gebruiker_ids)))
        conn.execute(wachtwoord_reset_tokens.delete().where(wachtwoord_reset_tokens.c.gebruiker_id.in_(gebruiker_ids)))
        conn.execute(gebruiker_winkels.delete().where(gebruiker_winkels.c.winkel_id.in_(winkel_ids)))
        conn.execute(api_keys.delete().where(api_keys.c.organisatie_id == organisatie_id))
        conn.execute(eigen_verkoopdata.delete().where(eigen_verkoopdata.c.organisatie_id == organisatie_id))
        conn.execute(eigen_product_verkoopdata.delete().where(eigen_product_verkoopdata.c.organisatie_id == organisatie_id))
        conn.execute(winkels.delete().where(winkels.c.organisatie_id == organisatie_id))
        conn.execute(gebruikers.delete().where(gebruikers.c.organisatie_id == organisatie_id))
        conn.execute(
            aanmeldingen.update().where(aanmeldingen.c.organisatie_id == organisatie_id).values(organisatie_id=None)
        )
        conn.execute(organisaties.delete().where(organisaties.c.id == organisatie_id))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_organisaties.py -v'"
```

Expected: PASS — all tests in the file, including every test from Tasks 1 and 2.

- [ ] **Step 6: Commit**

```bash
git add db/organisaties.py tests/test_db_organisaties.py
git commit -m "feat: add verwijder_organisatie cascade-delete function"
```

---

### Task 4: `db/opschonen_cli.py` cron entrypoint

**Files:**
- Create: `db/opschonen_cli.py`
- Test: `tests/test_opschonen_cli.py`

**Interfaces:**
- Consumes: `db.organisaties.haal_te_verwijderen_organisaties(engine, nu, wachtdagen=30) -> list[int]` (Task 2); `db.organisaties.verwijder_organisatie(engine, organisatie_id) -> None` (Task 3); `db.schema.maak_database(database_pad: Path) -> Engine`.
- Produces: `main() -> list[int]` (the ids of organizations actually deleted), and `if __name__ == "__main__": main()` — the module is invoked as `python3 -m db.opschonen_cli`, consumed by Task 5's cron line.

- [ ] **Step 1: Write the failing test**

Create `tests/test_opschonen_cli.py`:

```python
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from db import opschonen_cli
from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.organisaties import deactiveer_organisatie
from db.schema import gebruikers, maak_database, organisaties


def _maak_gedeactiveerde_organisatie(engine, naam, slug, dagen_geleden):
    org_id = bootstrap_organisatie(engine, naam=naam, slug=slug, store_ids=[])
    deactiveer_organisatie(engine, organisatie_id=org_id)
    verleden = datetime.now(timezone.utc) - timedelta(days=dagen_geleden)
    with engine.begin() as conn:
        conn.execute(organisaties.update().where(organisaties.c.id == org_id).values(gedeactiveerd_op=verleden))
    return org_id


def test_main_verwijdert_organisatie_over_wachtperiode(tmp_path, monkeypatch):
    db_pad = tmp_path / "tenants.db"
    engine = maak_database(db_pad)
    org_id = _maak_gedeactiveerde_organisatie(engine, "Klant", "klant", dagen_geleden=31)
    monkeypatch.setenv("TENANTS_DB_PAD", str(db_pad))

    verwijderd = opschonen_cli.main()

    assert verwijderd == [org_id]
    with engine.connect() as conn:
        assert conn.execute(select(organisaties).where(organisaties.c.id == org_id)).first() is None


def test_main_laat_recent_gedeactiveerde_organisatie_staan(tmp_path, monkeypatch):
    db_pad = tmp_path / "tenants.db"
    engine = maak_database(db_pad)
    org_id = _maak_gedeactiveerde_organisatie(engine, "Klant", "klant", dagen_geleden=5)
    monkeypatch.setenv("TENANTS_DB_PAD", str(db_pad))

    verwijderd = opschonen_cli.main()

    assert verwijderd == []
    with engine.connect() as conn:
        assert conn.execute(select(organisaties).where(organisaties.c.id == org_id)).first() is not None


def test_main_gaat_door_na_fout_bij_een_organisatie(tmp_path, monkeypatch):
    db_pad = tmp_path / "tenants.db"
    engine = maak_database(db_pad)
    org_a = _maak_gedeactiveerde_organisatie(engine, "Org A", "org-a", dagen_geleden=31)
    org_b = _maak_gedeactiveerde_organisatie(engine, "Org B", "org-b", dagen_geleden=31)
    monkeypatch.setenv("TENANTS_DB_PAD", str(db_pad))

    origineel = opschonen_cli.verwijder_organisatie
    def _mislukt_voor_org_a(engine, organisatie_id):
        if organisatie_id == org_a:
            raise RuntimeError("gesimuleerde databasefout")
        origineel(engine, organisatie_id)
    monkeypatch.setattr(opschonen_cli, "verwijder_organisatie", _mislukt_voor_org_a)

    verwijderd = opschonen_cli.main()

    assert verwijderd == [org_b]


def test_main_logt_geen_naam_of_email(tmp_path, monkeypatch, capsys):
    db_pad = tmp_path / "tenants.db"
    engine = maak_database(db_pad)
    org_id = _maak_gedeactiveerde_organisatie(engine, "Geheime Bakkerij BV", "geheime-bakkerij", dagen_geleden=31)
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@geheimebakkerij.nl", wachtwoord="geheim123")
    # verwijder_organisatie() draait vóór het printen, dus de e-mail bestaat
    # op het moment van loggen niet meer in de database — deze test bevestigt
    # bovendien dat de geloggde tekst zelf die waarden nooit noemt.
    monkeypatch.setenv("TENANTS_DB_PAD", str(db_pad))

    opschonen_cli.main()

    output = capsys.readouterr().out
    assert "Geheime Bakkerij BV" not in output
    assert "eigenaar@geheimebakkerij.nl" not in output
    assert str(org_id) in output
```

- [ ] **Step 2: Run test to verify it fails**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_opschonen_cli.py -v'"
```

Expected: FAIL with `ModuleNotFoundError: No module named 'db.opschonen_cli'`.

- [ ] **Step 3: Implement `db/opschonen_cli.py`**

Create `db/opschonen_cli.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_opschonen_cli.py -v'"
```

Expected: PASS — all four tests.

- [ ] **Step 5: Run the full test suite**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest -q'"
```

Run this in the foreground and wait for it to finish — do not background it. Expected: every test in the project passes, no regressions from Tasks 1–4.

- [ ] **Step 6: Commit**

```bash
git add db/opschonen_cli.py tests/test_opschonen_cli.py
git commit -m "feat: add db.opschonen_cli daily cascade-delete cron entrypoint"
```

---

### Task 5: Deploy docs, production deployment, and manual verification

**Files:**
- Modify: `deploy/DEPLOY.md`

**Interfaces:** none new — this task ships and verifies everything built in Tasks 1–4.

- [ ] **Step 1: Add the new cron section to `deploy/DEPLOY.md`**

Find the existing section (currently section 8, immediately before `## Bekende beperkingen van deze live opzet`):

```
## 8. Wekelijkse herbestel-mail inplannen (Fase 5 NODIG 3)

Geen scheduler in de app zelf (bewust — geen extra always-on service voor
deze schaal) — een cron-regel op de host draait `serving.herbestel_email_cli`
elke maandagochtend binnen de al draaiende `api`-container:
```bash
crontab -e
# 0 7 * * 1 cd /home/job/forecasting-demo && docker compose exec -T api \
#   python3 -m serving.herbestel_email_cli >> /home/job/forecasting-demo/herbestel-mail.log 2>&1
```
Vereist dat `MAIL_SMTP_*` in `.env` staat (stap 3) — zonder mailconfig
verstuurt `security/mail.py` simpelweg niets (elke organisatie wordt dan
overgeslagen met een `MailNietGeconfigureerd`-regel in het logbestand,
geen crash). Test één keer handmatig vóór je de cron-regel aanzet:
```bash
docker compose exec api python3 -m serving.herbestel_email_cli
```
```

Immediately after it (still before `## Bekende beperkingen van deze live opzet`), add:

```markdown
## 9. Dagelijkse opschoning van gedeactiveerde organisaties inplannen (AVG)

Zelfde patroon als stap 8 — een cron-regel op de host draait
`db.opschonen_cli` elke nacht binnen de al draaiende `api`-container. Dit
verwijdert organisaties **definitief en onomkeerbaar** (AVG-vereiste, zie
`FASE4-SAAS-FOUNDATION.md` beslissing 9) 30 dagen nadat Stripe
`customer.subscription.deleted` meldde:
```bash
crontab -e
# 0 3 * * * cd /home/job/forecasting-demo && docker compose exec -T api \
#   python3 -m db.opschonen_cli >> /home/job/forecasting-demo/opschonen.log 2>&1
```
Dagelijks, niet wekelijks zoals stap 8 — een verwijdering hoeft niet
wekenlang na de wachtperiode te blijven hangen. Test één keer handmatig
vóór je de cron-regel aanzet:
```bash
docker compose exec api python3 -m db.opschonen_cli
```
Verwacht bij een lege/verse database: `0 organisatie(s) verwijderd: (geen)`.
```

- [ ] **Step 2: Commit the doc change**

```bash
git add deploy/DEPLOY.md
git commit -m "docs: add daily cascade-delete cron section to DEPLOY.md"
```

- [ ] **Step 3: Deploy the changed backend files to production**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/db/schema.py \
    /Users/hamdeco/development/hamdoun/forecasting/db/organisaties.py \
    /Users/hamdeco/development/hamdoun/forecasting/db/opschonen_cli.py \
    job@157.90.244.24:/home/job/forecasting-demo/db/

ssh job@157.90.244.24 "cd /home/job/forecasting-demo/deploy && docker compose build api && docker compose up -d"
```

- [ ] **Step 4: Run the manual verification, per DEPLOY.md's own convention**

```bash
ssh job@157.90.244.24 "cd /home/job/forecasting-demo/deploy && docker compose exec api python3 -m db.opschonen_cli"
```

Expected output: `0 organisatie(s) verwijderd: (geen)` — the container rebuild in Step 3 already ran `maak_database()` on startup (via `serving/app.py`'s module-level `laad_settings()`/`maak_database()` calls), which auto-adds the new `gedeactiveerd_op` column via `_migreer_ontbrekende_kolommen()`. A clean run with no errors and this exact output confirms the column exists, the query runs correctly, and — since there should be no organizations 30+ days past deactivation on this fresh feature — nothing gets deleted. If any real organization actually is currently past the 30-day mark, this command will delete it for real; check the output line-by-line before proceeding if the count is nonzero.

- [ ] **Step 5: Enable the cron line**

```bash
ssh job@157.90.244.24 "crontab -l"
```

Confirm the existing herbestel-mail line (`0 7 * * 1 ...`) is present, then add the new line from Step 1 above (`0 3 * * * ...`) via `crontab -e` on the server. Re-run `crontab -l` to confirm both lines are now present.

- [ ] **Step 6: Final verification**

```bash
ssh job@157.90.244.24 "tail -5 /home/job/forecasting-demo/opschonen.log 2>&1 || echo 'logfile not yet created — expected, first cron run is tonight at 03:00'"
curl -s https://prospero.tessar.nl/health
```

Confirm the health check still returns `{"status":"ok", ...}` — this deploy touched `db/organisaties.py`, which `serving/app.py` imports indirectly through the webhook handler, so a full health check confirms the rebuilt container starts cleanly.
---

## Self-Review

**Spec coverage:** Every spec section maps to a task. Architecture's three pieces (column, `verwijder_organisatie()`, `opschonen_cli.py`) are Tasks 1/3/4. Components' file-by-file breakdown matches exactly. Data flow steps 1–3 are Tasks 1/5/3; step 4 (no change to existing access-control paths) requires no new code since `serving/app.py`'s login/session checks are never touched — confirmed by omission, not a gap. Error handling's transaction atomicity is Task 3's single `engine.begin()`; the per-org catch-and-continue is explicitly tested in Task 4 (`test_main_gaat_door_na_fout_bij_een_organisatie`); the late-webhook-retry race needs no new code since the existing `haal_organisatie_id_bij_stripe_subscription()` already returns `None` for an unknown id. The spec's two log-content requirements (only `organisatie_id`, never name/email) are directly tested in `test_main_logt_geen_naam_of_email`. Testing section's two file targets are Tasks 1–3 (extends `tests/test_db_organisaties.py`) and Task 4 (creates `tests/test_opschonen_cli.py`), including the spec-mandated cross-organization isolation scenario.

**Placeholder scan:** No TBD/TODO markers. Every step has complete, runnable code — no "add appropriate handling" language anywhere.

**Type consistency:** `haal_te_verwijderen_organisaties(engine, nu, wachtdagen=30) -> list[int]` (Task 2) is called in Task 4 exactly as `haal_te_verwijderen_organisaties(engine, nu)`, relying on the same default. `verwijder_organisatie(engine, organisatie_id) -> None` (Task 3) is called in Task 4 with matching argument names. `deactiveer_organisatie(engine, organisatie_id)`'s signature is unchanged (only its body changes), so the existing webhook-handler call site in `serving/app.py` needs no edit — confirmed by omission from the File Structure list.
