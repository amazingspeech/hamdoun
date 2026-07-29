# Eigen winkels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single organisation-wide "eigen verkoopdata" bucket with multiple named "eigen winkels", each with independent uploaded sales history, and derive the herbestel-prijs automatically from uploaded data where possible.

**Architecture:** A new `eigen_winkels` table (name only, no ML-model link) becomes the scoping key for `eigen_verkoopdata`/`eigen_product_verkoopdata` (replacing `organisatie_id`) and for a new `eigen_winkel_instellingen` table (replacing the org-wide price column). New CRUD endpoints manage eigen winkels; existing upload/read endpoints gain a required `eigen_winkel_id`. Two already-shipped features (the weekly herbestel-mail cron and the onboarding checklist) are updated in the same pass since they read the structures being replaced. Frontend gets a new management card plus a winkel-selector on the existing two upload cards.

**Tech Stack:** Python 3.9, FastAPI, SQLAlchemy Core (no ORM), SQLite, pytest, vanilla JS (no framework, no build step) for the dashboard.

**Reference spec:** `forecasting/docs/superpowers/specs/2026-07-29-eigen-winkels-design.md`

## Global Constraints

- All code, identifiers, docstrings, and UI copy in Dutch, matching the existing codebase exactly (`eigen_winkel`, not `eigen_store` or similar).
- SQLAlchemy Core only — no ORM classes, mirrors every existing `db/*.py` module.
- A resource that doesn't exist or belongs to another organisation returns 404, never 403 (enumeration-prevention convention used everywhere else in `serving/app.py`).
- TDD throughout: write the failing test first, watch it fail, then implement. Every task below is already ordered red→green.
- Run tests with: `DYLD_LIBRARY_PATH=/Users/hamdeco/.homebrew/opt/libomp/lib PYTHONPATH=.venv/lib/python3.9/site-packages /usr/bin/python3 -m pytest -q <path>` from `forecasting/`.
- Commit after every task (not every step) with a Dutch, present-tense-implying message matching the existing git log style.

---

### Task 1: Schema — `eigen_winkels`, `eigen_winkel_instellingen`, restructured verkoopdata tables

**Files:**
- Modify: `db/schema.py`
- Test: `tests/test_db_schema.py`

**Interfaces:**
- Produces: `eigen_winkels` table (`id`, `organisatie_id` FK, `naam` String not-null, `aangemaakt_op`), unique on `(organisatie_id, naam)`. `eigen_winkel_instellingen` table (`eigen_winkel_id` FK **and primary key**, `gemiddelde_omzet_per_stuk` Float nullable). `eigen_verkoopdata`/`eigen_product_verkoopdata` scoped by `eigen_winkel_id` instead of `organisatie_id`.

- [ ] **Step 1: Write the failing schema test**

Add to `tests/test_db_schema.py` (mirror the style of existing table-shape assertions already in that file — inspect one existing test in the file first for the exact `inspect(engine)` pattern used, then add):

```python
def test_eigen_winkels_tabel_bestaat_met_verwachte_kolommen(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    inspector = inspect(engine)
    kolommen = {k["name"] for k in inspector.get_columns("eigen_winkels")}
    assert kolommen == {"id", "organisatie_id", "naam", "aangemaakt_op"}


def test_eigen_winkel_instellingen_tabel_bestaat_met_verwachte_kolommen(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    inspector = inspect(engine)
    kolommen = {k["name"] for k in inspector.get_columns("eigen_winkel_instellingen")}
    assert kolommen == {"eigen_winkel_id", "gemiddelde_omzet_per_stuk"}


def test_eigen_verkoopdata_is_gescoped_op_eigen_winkel_id(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    inspector = inspect(engine)
    kolommen = {k["name"] for k in inspector.get_columns("eigen_verkoopdata")}
    assert "eigen_winkel_id" in kolommen
    assert "organisatie_id" not in kolommen


def test_eigen_product_verkoopdata_is_gescoped_op_eigen_winkel_id(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    inspector = inspect(engine)
    kolommen = {k["name"] for k in inspector.get_columns("eigen_product_verkoopdata")}
    assert "eigen_winkel_id" in kolommen
    assert "organisatie_id" not in kolommen


def test_organisaties_heeft_geen_gemiddelde_omzet_per_stuk_kolom_meer(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    inspector = inspect(engine)
    kolommen = {k["name"] for k in inspector.get_columns("organisaties")}
    assert "gemiddelde_omzet_per_stuk" not in kolommen
```

Check that `inspect` is already imported at the top of `tests/test_db_schema.py` (it's used by `db/schema.py` itself, so it's very likely already imported in this test file too — add the import if not).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db_schema.py -k "eigen_winkel or gemiddelde_omzet_per_stuk_kolom" -v`
Expected: FAIL — `eigen_winkels`/`eigen_winkel_instellingen` tables don't exist yet, `eigen_verkoopdata` still has `organisatie_id`, `organisaties` still has `gemiddelde_omzet_per_stuk`.

- [ ] **Step 3: Edit `db/schema.py`**

Remove the `gemiddelde_omzet_per_stuk` column (and its comment) from the `organisaties` table definition (currently around line 42-49).

Add two new tables, placed right after the `winkels` table definition (around line 94, before `api_keys`):

```python
eigen_winkels = Table(
    "eigen_winkels",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("organisatie_id", Integer, ForeignKey("organisaties.id"), nullable=False),
    # Geen ML-model-koppeling (in tegenstelling tot `winkels` hierboven) —
    # puur een naam om zelf geüploade verkoopdata onder te groeperen. Zie
    # docs/superpowers/specs/2026-07-29-eigen-winkels-design.md.
    Column("naam", String, nullable=False),
    Column("aangemaakt_op", DateTime, nullable=False),
    UniqueConstraint("organisatie_id", "naam", name="uq_organisatie_eigen_winkel_naam"),
)

eigen_winkel_instellingen = Table(
    "eigen_winkel_instellingen",
    metadata,
    # eigen_winkel_id is zowel primary key als FK: hoogstens één
    # instellingen-rij per eigen winkel, geen aparte surrogate id nodig.
    Column("eigen_winkel_id", Integer, ForeignKey("eigen_winkels.id"), primary_key=True),
    Column("gemiddelde_omzet_per_stuk", Float, nullable=True),
)
```

Modify the existing `eigen_verkoopdata` table (replace the `organisatie_id` column and its `UniqueConstraint`):

```python
eigen_verkoopdata = Table(
    "eigen_verkoopdata",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("eigen_winkel_id", Integer, ForeignKey("eigen_winkels.id"), nullable=False),
    Column("datum", String, nullable=False),
    Column("omzet", Float, nullable=False),
    Column("aangemaakt_op", DateTime, nullable=False),
    UniqueConstraint("eigen_winkel_id", "datum", name="uq_eigen_winkel_datum"),
)
```

Modify `eigen_product_verkoopdata` the same way:

```python
eigen_product_verkoopdata = Table(
    "eigen_product_verkoopdata",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("eigen_winkel_id", Integer, ForeignKey("eigen_winkels.id"), nullable=False),
    Column("datum", String, nullable=False),
    Column("product", String, nullable=False),
    Column("aantal", Integer, nullable=False),
    Column("aangemaakt_op", DateTime, nullable=False),
    UniqueConstraint("eigen_winkel_id", "product", "datum", name="uq_eigen_winkel_product_datum"),
)
```

Keep every other column comment/docstring in both tables unchanged — only the scoping column and constraint change.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_db_schema.py -v`
Expected: PASS, including all pre-existing schema tests (nothing else in the file should be affected).

- [ ] **Step 5: Commit**

```bash
git add db/schema.py tests/test_db_schema.py
git commit -m "forecasting: herstructureer eigen-verkoopdata-schema rond eigen_winkels"
```

---

### Task 2: `db/eigen_winkels.py` — maken, lijsten, hernoemen, verwijderen

**Files:**
- Create: `db/eigen_winkels.py`
- Test: `tests/test_db_eigen_winkels.py`

**Interfaces:**
- Consumes: `db.schema.eigen_winkels`, `eigen_verkoopdata`, `eigen_product_verkoopdata`, `eigen_winkel_instellingen` (Task 1). `db.bootstrap.bootstrap_organisatie(engine, naam, slug, store_ids) -> int` (existing, for test fixtures).
- Produces: `maak_eigen_winkel(engine, organisatie_id, naam) -> int` (raises `sqlalchemy.exc.IntegrityError` on duplicate name within the org). `lijst_eigen_winkels(engine, organisatie_id) -> list[dict]` with keys `id`, `naam`, `heeft_verkoopdata`. `hernoem_eigen_winkel(engine, organisatie_id, eigen_winkel_id, nieuwe_naam) -> bool` (raises `IntegrityError` on collision, returns `False` if not found/not owned). `verwijder_eigen_winkel(engine, organisatie_id, eigen_winkel_id) -> bool`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_db_eigen_winkels.py`:

```python
import pytest
from sqlalchemy.exc import IntegrityError

from db.bootstrap import bootstrap_organisatie
from db.eigen_winkels import (
    hernoem_eigen_winkel,
    lijst_eigen_winkels,
    maak_eigen_winkel,
    verwijder_eigen_winkel,
)
from db.schema import eigen_product_verkoopdata, eigen_verkoopdata, maak_database
from db.verkoopdata import vervang_verkoopdata


def test_maak_eigen_winkel_geeft_nieuw_id_terug(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])

    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    assert isinstance(winkel_id, int)


def test_maak_eigen_winkel_dubbele_naam_binnen_organisatie_faalt(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    with pytest.raises(IntegrityError):
        maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")


def test_maak_eigen_winkel_zelfde_naam_andere_organisatie_mag(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Klant A", slug="klant-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Klant B", slug="klant-b", store_ids=[])
    maak_eigen_winkel(engine, organisatie_id=org_a, naam="Webshop A")

    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_b, naam="Webshop A")

    assert isinstance(winkel_id, int)


def test_lijst_eigen_winkels_geeft_alleen_winkels_van_die_organisatie(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Klant A", slug="klant-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Klant B", slug="klant-b", store_ids=[])
    maak_eigen_winkel(engine, organisatie_id=org_a, naam="Webshop A")
    maak_eigen_winkel(engine, organisatie_id=org_b, naam="Webshop B")

    winkels = lijst_eigen_winkels(engine, organisatie_id=org_a)

    assert [w["naam"] for w in winkels] == ["Webshop A"]


def test_lijst_eigen_winkels_heeft_verkoopdata_klopt(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    winkels = lijst_eigen_winkels(engine, organisatie_id=org_id)
    assert winkels[0]["heeft_verkoopdata"] is False

    vervang_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=[("2026-06-01", 100.0)])
    winkels = lijst_eigen_winkels(engine, organisatie_id=org_id)
    assert winkels[0]["heeft_verkoopdata"] is True


def test_hernoem_eigen_winkel_wijzigt_naam(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    gelukt = hernoem_eigen_winkel(engine, organisatie_id=org_id, eigen_winkel_id=winkel_id, nieuwe_naam="Webshop B")

    assert gelukt is True
    assert lijst_eigen_winkels(engine, organisatie_id=org_id)[0]["naam"] == "Webshop B"


def test_hernoem_eigen_winkel_andere_organisatie_geeft_false(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Klant A", slug="klant-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Klant B", slug="klant-b", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_a, naam="Webshop A")

    gelukt = hernoem_eigen_winkel(engine, organisatie_id=org_b, eigen_winkel_id=winkel_id, nieuwe_naam="Overname")

    assert gelukt is False
    assert lijst_eigen_winkels(engine, organisatie_id=org_a)[0]["naam"] == "Webshop A"


def test_verwijder_eigen_winkel_verwijdert_ook_verkoopdata(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")
    vervang_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=[("2026-06-01", 100.0)])

    gelukt = verwijder_eigen_winkel(engine, organisatie_id=org_id, eigen_winkel_id=winkel_id)

    assert gelukt is True
    assert lijst_eigen_winkels(engine, organisatie_id=org_id) == []
    with engine.connect() as conn:
        from sqlalchemy import select
        assert conn.execute(select(eigen_verkoopdata)).all() == []


def test_verwijder_eigen_winkel_andere_organisatie_geeft_false(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Klant A", slug="klant-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Klant B", slug="klant-b", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_a, naam="Webshop A")

    gelukt = verwijder_eigen_winkel(engine, organisatie_id=org_b, eigen_winkel_id=winkel_id)

    assert gelukt is False
    assert len(lijst_eigen_winkels(engine, organisatie_id=org_a)) == 1
```

Note: `vervang_verkoopdata(engine, eigen_winkel_id=..., rijen=...)` is the Task 4 signature (`organisatie_id` param renamed to `eigen_winkel_id`) — this test file therefore depends on Task 4 being done first, or being done together. Do Task 4 immediately before running this test file if executing tasks out of the listed order; the plan lists Task 2 first only because `db/eigen_winkels.py` has no dependency the other direction.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db_eigen_winkels.py -v`
Expected: FAIL — `db/eigen_winkels.py` doesn't exist yet (`ModuleNotFoundError`).

- [ ] **Step 3: Write `db/eigen_winkels.py`**

```python
"""Eigen winkels: een naam-baar concept los van het ML-model-gekoppelde
`winkels`, puur om zelf geüploade verkoopdata onder te groeperen — zie
docs/superpowers/specs/2026-07-29-eigen-winkels-design.md."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import eigen_product_verkoopdata, eigen_verkoopdata, eigen_winkel_instellingen, eigen_winkels


def maak_eigen_winkel(engine: Engine, organisatie_id: int, naam: str) -> int:
    with engine.begin() as conn:
        return conn.execute(
            eigen_winkels.insert().values(
                organisatie_id=organisatie_id, naam=naam, aangemaakt_op=datetime.now(timezone.utc)
            )
        ).inserted_primary_key[0]


def lijst_eigen_winkels(engine: Engine, organisatie_id: int) -> list[dict]:
    with engine.connect() as conn:
        winkels = conn.execute(
            select(eigen_winkels.c.id, eigen_winkels.c.naam)
            .where(eigen_winkels.c.organisatie_id == organisatie_id)
            .order_by(eigen_winkels.c.naam)
        ).all()
        resultaat = []
        for winkel in winkels:
            heeft_verkoopdata = conn.execute(
                select(eigen_verkoopdata.c.id).where(eigen_verkoopdata.c.eigen_winkel_id == winkel.id)
            ).first() is not None
            resultaat.append({"id": winkel.id, "naam": winkel.naam, "heeft_verkoopdata": heeft_verkoopdata})
    return resultaat


def hernoem_eigen_winkel(engine: Engine, organisatie_id: int, eigen_winkel_id: int, nieuwe_naam: str) -> bool:
    with engine.begin() as conn:
        resultaat = conn.execute(
            eigen_winkels.update()
            .where(eigen_winkels.c.id == eigen_winkel_id, eigen_winkels.c.organisatie_id == organisatie_id)
            .values(naam=nieuwe_naam)
        )
    return resultaat.rowcount > 0


def verwijder_eigen_winkel(engine: Engine, organisatie_id: int, eigen_winkel_id: int) -> bool:
    """Verwijdert de winkel en, in dezelfde transactie, al zijn
    verkoopdata + instellingen — zelfde reden als db.organisaties.
    verwijder_organisatie(): nooit een tussentoestand met wees-rijen."""
    with engine.begin() as conn:
        rij = conn.execute(
            select(eigen_winkels.c.id).where(
                eigen_winkels.c.id == eigen_winkel_id, eigen_winkels.c.organisatie_id == organisatie_id
            )
        ).first()
        if rij is None:
            return False
        conn.execute(eigen_verkoopdata.delete().where(eigen_verkoopdata.c.eigen_winkel_id == eigen_winkel_id))
        conn.execute(
            eigen_product_verkoopdata.delete().where(eigen_product_verkoopdata.c.eigen_winkel_id == eigen_winkel_id)
        )
        conn.execute(
            eigen_winkel_instellingen.delete().where(eigen_winkel_instellingen.c.eigen_winkel_id == eigen_winkel_id)
        )
        conn.execute(eigen_winkels.delete().where(eigen_winkels.c.id == eigen_winkel_id))
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_db_eigen_winkels.py -v`
Expected: PASS (after Task 4's `vervang_verkoopdata` signature change is also in place — see the note in Step 1).

- [ ] **Step 5: Commit**

```bash
git add db/eigen_winkels.py tests/test_db_eigen_winkels.py
git commit -m "forecasting: voeg db/eigen_winkels.py toe (maken/lijsten/hernoemen/verwijderen)"
```

---

### Task 3: `db/eigen_winkel_instellingen.py` — prijs per eigen winkel

**Files:**
- Create: `db/eigen_winkel_instellingen.py`
- Modify: `db/organisaties.py` (remove `stel_gemiddelde_omzet_per_stuk_in`/`haal_gemiddelde_omzet_per_stuk`, remove now-unused `Optional`/`Float` imports if any become unused — check before removing)
- Test: `tests/test_db_eigen_winkel_instellingen.py`
- Test: `tests/test_db_organisaties.py` (remove the two tests covering the functions being deleted)

**Interfaces:**
- Consumes: `db.schema.eigen_winkel_instellingen` (Task 1).
- Produces: `stel_prijs_in(engine, eigen_winkel_id, bedrag) -> None`. `haal_prijs(engine, eigen_winkel_id) -> float | None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_db_eigen_winkel_instellingen.py`:

```python
from db.bootstrap import bootstrap_organisatie
from db.eigen_winkel_instellingen import haal_prijs, stel_prijs_in
from db.eigen_winkels import maak_eigen_winkel
from db.schema import maak_database


def test_haal_prijs_zonder_instelling_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    assert haal_prijs(engine, eigen_winkel_id=winkel_id) is None


def test_stel_prijs_in_en_haal_weer_op(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")

    stel_prijs_in(engine, eigen_winkel_id=winkel_id, bedrag=24.5)

    assert haal_prijs(engine, eigen_winkel_id=winkel_id) == 24.5


def test_stel_prijs_in_overschrijft_bestaande_waarde(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")
    stel_prijs_in(engine, eigen_winkel_id=winkel_id, bedrag=24.5)

    stel_prijs_in(engine, eigen_winkel_id=winkel_id, bedrag=30.0)

    assert haal_prijs(engine, eigen_winkel_id=winkel_id) == 30.0
```

Remove `test_stel_gemiddelde_omzet_per_stuk_in_*`/`test_haal_gemiddelde_omzet_per_stuk_*`-style tests from `tests/test_db_organisaties.py` (search for `gemiddelde_omzet_per_stuk` in that file first to find their exact names).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db_eigen_winkel_instellingen.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Write `db/eigen_winkel_instellingen.py`, edit `db/organisaties.py`**

```python
"""Gemiddelde omzet per verkocht stuk, per eigen winkel (zie
db/eigen_winkels.py) — vervangt het vroegere org-brede veld op
`organisaties`. `stel_prijs_in` doet een insert-of-update ("upsert" via
delete+insert binnen één transactie, consistent met hoe de rest van dit
project geen SQLite-specifieke ON CONFLICT-syntax gebruikt) omdat de rij
pas bestaat zodra een prijs voor het eerst gezet wordt."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import eigen_winkel_instellingen


def stel_prijs_in(engine: Engine, eigen_winkel_id: int, bedrag: float) -> None:
    with engine.begin() as conn:
        conn.execute(
            eigen_winkel_instellingen.delete().where(eigen_winkel_instellingen.c.eigen_winkel_id == eigen_winkel_id)
        )
        conn.execute(
            eigen_winkel_instellingen.insert().values(eigen_winkel_id=eigen_winkel_id, gemiddelde_omzet_per_stuk=bedrag)
        )


def haal_prijs(engine: Engine, eigen_winkel_id: int) -> Optional[float]:
    with engine.connect() as conn:
        return conn.execute(
            select(eigen_winkel_instellingen.c.gemiddelde_omzet_per_stuk).where(
                eigen_winkel_instellingen.c.eigen_winkel_id == eigen_winkel_id
            )
        ).scalar_one_or_none()
```

In `db/organisaties.py`: delete the `stel_gemiddelde_omzet_per_stuk_in()` and `haal_gemiddelde_omzet_per_stuk()` functions (currently lines 36-49). Leave everything else in the file untouched — Task 5 will edit `verwijder_organisatie()` in this same file separately.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_db_eigen_winkel_instellingen.py tests/test_db_organisaties.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add db/eigen_winkel_instellingen.py db/organisaties.py tests/test_db_eigen_winkel_instellingen.py tests/test_db_organisaties.py
git commit -m "forecasting: verplaats gemiddelde-omzet-per-stuk naar db/eigen_winkel_instellingen.py"
```

---

### Task 4: `db/verkoopdata.py` + `db/product_verkoopdata.py` — scope op `eigen_winkel_id`

**Files:**
- Modify: `db/verkoopdata.py`
- Modify: `db/product_verkoopdata.py`
- Test: `tests/test_db_verkoopdata.py`
- Test: `tests/test_db_product_verkoopdata.py`

**Interfaces:**
- Produces: `vervang_verkoopdata(engine, eigen_winkel_id, rijen)`, `haal_verkoopdata(engine, eigen_winkel_id) -> list[dict]` (was `organisatie_id`). `vervang_product_verkoopdata(engine, eigen_winkel_id, rijen)`, `haal_product_verkoopdata(engine, eigen_winkel_id) -> list[dict]` (was `organisatie_id`).

- [ ] **Step 1: Update the failing tests**

In `tests/test_db_verkoopdata.py` and `tests/test_db_product_verkoopdata.py`: every call site currently passes `organisatie_id=org_id` (from `bootstrap_organisatie`) directly to `vervang_verkoopdata`/`haal_verkoopdata`/`vervang_product_verkoopdata`/`haal_product_verkoopdata`. Replace each with a two-step setup: `winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")`, then pass `eigen_winkel_id=winkel_id` to the verkoopdata calls instead of `organisatie_id=org_id`. Add `from db.eigen_winkels import maak_eigen_winkel` to both files' imports. Keep every assertion unchanged — only the setup/call-site parameter changes.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db_verkoopdata.py tests/test_db_product_verkoopdata.py -v`
Expected: FAIL — `TypeError: vervang_verkoopdata() got an unexpected keyword argument 'eigen_winkel_id'` (functions still take `organisatie_id`).

- [ ] **Step 3: Edit `db/verkoopdata.py`**

```python
"""Fase 5 NODIG 2 (afgeslankt): opslag voor handmatig geüploade eigen
verkoopdata, per eigen winkel (zie db/eigen_winkels.py — zie
serving/verkoopdata.py voor de CSV-parser)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import eigen_verkoopdata


def vervang_verkoopdata(engine: Engine, eigen_winkel_id: int, rijen: list[tuple[str, float]]) -> None:
    """Vervangt de volledige verkoopdata van een eigen winkel door precies
    de opgegeven rijen — een nieuwe upload vervangt de vorige set in
    plaats van ermee samen te voegen, zodat een winkelier niet zelf hoeft
    uit te zoeken welke datums al bestonden."""
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(eigen_verkoopdata.delete().where(eigen_verkoopdata.c.eigen_winkel_id == eigen_winkel_id))
        if not rijen:
            return
        conn.execute(
            eigen_verkoopdata.insert(),
            [{"eigen_winkel_id": eigen_winkel_id, "datum": datum, "omzet": omzet, "aangemaakt_op": nu}
             for datum, omzet in rijen],
        )


def haal_verkoopdata(engine: Engine, eigen_winkel_id: int) -> list[dict]:
    with engine.connect() as conn:
        rijen = conn.execute(
            select(eigen_verkoopdata.c.datum, eigen_verkoopdata.c.omzet)
            .where(eigen_verkoopdata.c.eigen_winkel_id == eigen_winkel_id)
            .order_by(eigen_verkoopdata.c.datum)
        ).all()
    return [{"datum": r.datum, "omzet": r.omzet} for r in rijen]
```

- [ ] **Step 4: Edit `db/product_verkoopdata.py`**

Replace the file's content (same shape as Step 3 above, `product`/`aantal` columns added):

```python
"""Fase 5 premium (herbestel-advies per product): opslag voor
per-product verkoopdata, per eigen winkel (zie db/eigen_winkels.py — zie
serving/product_verkoopdata.py voor de CSV-parser)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from db.schema import eigen_product_verkoopdata


def vervang_product_verkoopdata(engine: Engine, eigen_winkel_id: int, rijen: list[tuple[str, str, int]]) -> None:
    """Vervangt de volledige product-verkoopdata van een eigen winkel door
    precies de opgegeven rijen — zelfde vervang-i.p.v.-samenvoegen-gedrag
    als db.verkoopdata.vervang_verkoopdata."""
    nu = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            eigen_product_verkoopdata.delete().where(eigen_product_verkoopdata.c.eigen_winkel_id == eigen_winkel_id)
        )
        if not rijen:
            return
        conn.execute(
            eigen_product_verkoopdata.insert(),
            [{"eigen_winkel_id": eigen_winkel_id, "datum": datum, "product": product, "aantal": aantal, "aangemaakt_op": nu}
             for datum, product, aantal in rijen],
        )


def haal_product_verkoopdata(engine: Engine, eigen_winkel_id: int) -> list[dict]:
    with engine.connect() as conn:
        rijen = conn.execute(
            select(eigen_product_verkoopdata.c.datum, eigen_product_verkoopdata.c.product, eigen_product_verkoopdata.c.aantal)
            .where(eigen_product_verkoopdata.c.eigen_winkel_id == eigen_winkel_id)
            .order_by(eigen_product_verkoopdata.c.datum)
        ).all()
    return [{"datum": r.datum, "product": r.product, "aantal": r.aantal} for r in rijen]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_db_verkoopdata.py tests/test_db_product_verkoopdata.py tests/test_db_eigen_winkels.py -v`
Expected: PASS (this also unblocks Task 2's test file, which depends on `vervang_verkoopdata`'s new signature).

- [ ] **Step 6: Commit**

```bash
git add db/verkoopdata.py db/product_verkoopdata.py tests/test_db_verkoopdata.py tests/test_db_product_verkoopdata.py
git commit -m "forecasting: scope verkoopdata/product-verkoopdata op eigen_winkel_id i.p.v. organisatie_id"
```

---

### Task 5: Fix `verwijder_organisatie()` cascade for the new scoping column

**Files:**
- Modify: `db/organisaties.py`
- Test: `tests/test_db_organisaties.py`

**Interfaces:**
- Consumes: `db.schema.eigen_winkels` (Task 1), `db.eigen_winkels.maak_eigen_winkel` (Task 2), `db.verkoopdata.vervang_verkoopdata` (Task 4, new signature).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_db_organisaties.py` (check the file's existing imports first — it likely already imports `verwijder_organisatie`, `bootstrap_organisatie`, `eigen_verkoopdata` from `db.schema`):

```python
def test_verwijder_organisatie_verwijdert_ook_eigen_winkels_en_hun_verkoopdata(tmp_path):
    from db.eigen_winkels import maak_eigen_winkel, lijst_eigen_winkels
    from db.verkoopdata import vervang_verkoopdata

    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Klant", slug="klant", store_ids=[])
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")
    vervang_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=[("2026-06-01", 100.0)])
    deactiveer_organisatie(engine, organisatie_id=org_id)

    verwijder_organisatie(engine, organisatie_id=org_id)

    with engine.connect() as conn:
        assert conn.execute(select(eigen_verkoopdata)).all() == []
    # De organisatie zelf is weg, dus lijst_eigen_winkels via een
    # willekeurig ander org_id-toetsingspunt is hier niet zinvol; de
    # afwezigheid van eigen_verkoopdata-rijen hierboven is het kernbewijs.
```

(Adjust the exact `deactiveer_organisatie`/`select`/`eigen_verkoopdata` import names to match what the top of `tests/test_db_organisaties.py` already imports — reuse, don't duplicate imports.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db_organisaties.py -k eigen_winkels_en_hun_verkoopdata -v`
Expected: FAIL — `IntegrityError` or similar, because `verwijder_organisatie()` still tries `eigen_verkoopdata.c.organisatie_id` (a column that no longer exists after Task 1/4) or leaves the `eigen_winkels` row (and its now-orphaned verkoopdata) behind, violating the FK when `organisaties` is deleted.

- [ ] **Step 3: Edit `db/organisaties.py`**

In `verwijder_organisatie()` (currently lines 159-185), replace the two lines:
```python
conn.execute(eigen_verkoopdata.delete().where(eigen_verkoopdata.c.organisatie_id == organisatie_id))
conn.execute(eigen_product_verkoopdata.delete().where(eigen_product_verkoopdata.c.organisatie_id == organisatie_id))
```
with, right after the existing `winkel_ids = select(...)` line (so `eigen_winkel_ids` is defined alongside the other id subqueries at the top of the function):
```python
eigen_winkel_ids = select(eigen_winkels.c.id).where(eigen_winkels.c.organisatie_id == organisatie_id)
```
and then, in the same relative position the two deleted lines occupied:
```python
conn.execute(eigen_verkoopdata.delete().where(eigen_verkoopdata.c.eigen_winkel_id.in_(eigen_winkel_ids)))
conn.execute(eigen_product_verkoopdata.delete().where(eigen_product_verkoopdata.c.eigen_winkel_id.in_(eigen_winkel_ids)))
conn.execute(eigen_winkel_instellingen.delete().where(eigen_winkel_instellingen.c.eigen_winkel_id.in_(eigen_winkel_ids)))
conn.execute(eigen_winkels.delete().where(eigen_winkels.c.organisatie_id == organisatie_id))
```
Add `eigen_winkel_instellingen` and `eigen_winkels` to the `from db.schema import (...)` block at the top of the file (alphabetical, matching the existing import style).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_db_organisaties.py -v`
Expected: PASS, including all pre-existing tests in the file.

- [ ] **Step 5: Commit**

```bash
git add db/organisaties.py tests/test_db_organisaties.py
git commit -m "forecasting: fix verwijder_organisatie() cascade voor eigen_winkels"
```

---

### Task 6: `serving/prijs_per_stuk.py` — automatische prijsafleiding

**Files:**
- Create: `serving/prijs_per_stuk.py`
- Test: `tests/test_prijs_per_stuk.py`

**Interfaces:**
- Produces: `bereken_gemiddelde_prijs_per_stuk(verkoopdata_rijen: list[dict], product_verkoopdata_rijen: list[dict]) -> float | None`. `verkoopdata_rijen`: `[{"datum": "JJJJ-MM-DD", "omzet": float}, ...]` (shape of `db.verkoopdata.haal_verkoopdata()`). `product_verkoopdata_rijen`: `[{"datum": "JJJJ-MM-DD", "product": str, "aantal": int}, ...]` (shape of `db.product_verkoopdata.haal_product_verkoopdata()`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_prijs_per_stuk.py`:

```python
from serving.prijs_per_stuk import bereken_gemiddelde_prijs_per_stuk


def test_berekent_prijs_uit_overlappende_dagen():
    verkoopdata = [{"datum": "2026-06-01", "omzet": 100.0}, {"datum": "2026-06-02", "omzet": 200.0}]
    product_verkoopdata = [
        {"datum": "2026-06-01", "product": "A", "aantal": 5},
        {"datum": "2026-06-02", "product": "A", "aantal": 10},
        {"datum": "2026-06-02", "product": "B", "aantal": 5},
    ]

    prijs = bereken_gemiddelde_prijs_per_stuk(verkoopdata, product_verkoopdata)

    # omzet 300 over dagen met aantal-data (300), aantal 20 stuks -> 15.0
    assert prijs == 15.0


def test_negeert_dagen_die_niet_in_beide_sets_voorkomen():
    verkoopdata = [
        {"datum": "2026-06-01", "omzet": 100.0},
        {"datum": "2026-06-02", "omzet": 999.0},  # geen aantal-data voor deze dag
    ]
    product_verkoopdata = [{"datum": "2026-06-01", "product": "A", "aantal": 10}]

    prijs = bereken_gemiddelde_prijs_per_stuk(verkoopdata, product_verkoopdata)

    assert prijs == 10.0  # 100 omzet / 10 stuks, 999/dag-2 genegeerd


def test_geen_overlappende_dagen_geeft_none():
    verkoopdata = [{"datum": "2026-06-01", "omzet": 100.0}]
    product_verkoopdata = [{"datum": "2026-06-02", "product": "A", "aantal": 10}]

    assert bereken_gemiddelde_prijs_per_stuk(verkoopdata, product_verkoopdata) is None


def test_lege_sets_geeft_none():
    assert bereken_gemiddelde_prijs_per_stuk([], []) is None


def test_nul_totaal_aantal_geeft_none():
    verkoopdata = [{"datum": "2026-06-01", "omzet": 100.0}]
    product_verkoopdata = [{"datum": "2026-06-01", "product": "A", "aantal": 0}]

    assert bereken_gemiddelde_prijs_per_stuk(verkoopdata, product_verkoopdata) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_prijs_per_stuk.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Write `serving/prijs_per_stuk.py`**

```python
"""Automatische afleiding van de gemiddelde omzet per verkocht stuk uit
twee al bestaande, per eigen winkel geüploade datasets — zie
docs/superpowers/specs/2026-07-29-eigen-winkels-design.md sectie 3.
Losstaande, puur-functionele module (geen DB-toegang), zelfde stijl als
serving/verkoopdata.py."""
from __future__ import annotations

from collections import defaultdict
from typing import Optional


def bereken_gemiddelde_prijs_per_stuk(
    verkoopdata_rijen: list[dict], product_verkoopdata_rijen: list[dict]
) -> Optional[float]:
    """Sommeert omzet en aantal, uitsluitend over de datums die in beide
    sets voorkomen, en deelt de twee totalen. None zonder overlap of bij
    een totaal aantal van 0 — nooit een prijs verzinnen of door 0 delen."""
    aantal_per_datum: dict[str, int] = defaultdict(int)
    for rij in product_verkoopdata_rijen:
        aantal_per_datum[rij["datum"]] += rij["aantal"]

    totaal_omzet = 0.0
    totaal_aantal = 0
    for rij in verkoopdata_rijen:
        if rij["datum"] not in aantal_per_datum:
            continue
        totaal_omzet += rij["omzet"]
        totaal_aantal += aantal_per_datum[rij["datum"]]

    if totaal_aantal <= 0:
        return None
    return totaal_omzet / totaal_aantal
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_prijs_per_stuk.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add serving/prijs_per_stuk.py tests/test_prijs_per_stuk.py
git commit -m "forecasting: bereken gemiddelde prijs per stuk automatisch uit eigen data"
```

---

### Task 7: `serving/schemas.py` — nieuwe/gewijzigde Pydantic-modellen

**Files:**
- Modify: `serving/schemas.py`

**Interfaces:**
- Produces: `EigenWinkelAanmakenVerzoek {naam: str}`. `EigenWinkelHernoemenVerzoek {naam: str}`. `EigenWinkelInstellingenVerzoek {gemiddelde_omzet_per_stuk: float}` (reuses the `gt=0` validation the old `OrganisatieInstellingenVerzoek` had). `EigenWinkelResponse {id: int, naam: str, heeft_verkoopdata: bool, gemiddelde_omzet_per_stuk: Optional[float], automatische_prijs_per_stuk: Optional[float]}`.

- [ ] **Step 1: No test for this task**

Pydantic model definitions have no independent behavior to unit-test in this codebase's existing style (none of the other schema classes have dedicated tests) — correctness is exercised through the endpoint tests in Task 8/9. Proceed straight to editing.

- [ ] **Step 2: Edit `serving/schemas.py`**

Remove `OrganisatieInstellingenVerzoek` and `OrganisatieInstellingenResponse` (currently lines 111-116).

In their place, add:

```python
class EigenWinkelAanmakenVerzoek(BaseModel):
    naam: str = Field(..., min_length=1)


class EigenWinkelHernoemenVerzoek(BaseModel):
    naam: str = Field(..., min_length=1)


class EigenWinkelInstellingenVerzoek(BaseModel):
    gemiddelde_omzet_per_stuk: float = Field(..., gt=0)


class EigenWinkelResponse(BaseModel):
    id: int
    naam: str
    heeft_verkoopdata: bool
    gemiddelde_omzet_per_stuk: Optional[float] = None
    automatische_prijs_per_stuk: Optional[float] = None
```

Leave `VerkoopdataRij`, `VerkoopdataResponse`, `VerkoopdataUploadResponse`, `EigenVoorspellingDag`, `EigenVoorspellingResponse`, `ProductVerkoopdataUploadResponse`, `ProductHerbestelAdviesItem`, `ProductHerbestelAdviesResponse` unchanged — none of their fields change, only how the endpoints that produce them are parameterised (Task 9).

- [ ] **Step 3: Confirm the file still imports cleanly**

Run: `python3 -c "import serving.schemas"` (from `forecasting/`, with the venv's `PYTHONPATH` set as in Global Constraints).
Expected: no `ImportError`/`NameError`.

- [ ] **Step 4: Commit**

```bash
git add serving/schemas.py
git commit -m "forecasting: vervang OrganisatieInstellingen-schemas door EigenWinkel-schemas"
```

---

### Task 8: `serving/app.py` — eigen-winkels CRUD endpoints

**Files:**
- Modify: `serving/app.py`
- Test: `tests/test_eigen_winkels_endpoint.py`

**Interfaces:**
- Consumes: `db.eigen_winkels` (Task 2), `db.eigen_winkel_instellingen` (Task 3), `db.verkoopdata`/`db.product_verkoopdata` (Task 4), `serving.prijs_per_stuk.bereken_gemiddelde_prijs_per_stuk` (Task 6), schemas from Task 7, `GeauthenticeerdeGebruiker`/`vereis_sessie`/`vereis_eigenaar` (existing, `serving/app.py` lines 166-195).
- Produces: `POST /organisatie/eigen-winkels`, `GET /organisatie/eigen-winkels`, `PATCH /organisatie/eigen-winkels/{id}`, `DELETE /organisatie/eigen-winkels/{id}`, `PUT /organisatie/eigen-winkels/{id}/instellingen`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_eigen_winkels_endpoint.py`. Same two-organisation fixture shape as `tests/test_api_keys_endpoint.py` (organisatie A with an eigenaar and a lid, organisatie B with its own eigenaar, needed for the tenant-isolation tests below) — copied verbatim since it's a per-test-file local helper in this codebase, not a shared import:

```python
"""Zelfde fixture-vorm als tests/test_api_keys_endpoint.py."""
import importlib
import sys

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database
from training import artifact, train


def _bouw_omgeving(tmp_path, monkeypatch):
    modellen = train.train_alle_kwantielen(pd.DataFrame({
        **{k: np.random.default_rng(1).uniform(0, 100, 200) for k in train.FEATURE_KOLOMMEN},
        "Sales": np.random.default_rng(1).uniform(500, 2000, 200),
        "Open": 1,
    }))
    historie = pd.DataFrame({
        "Store": 1, "Date": pd.date_range("2015-06-01", periods=40, freq="D"),
        "Sales": np.random.default_rng(2).uniform(500, 2000, 40), "Open": 1,
    })
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    versie = artifact.schrijf_artefact(
        basis_map=tmp_path / "models", modellen=modellen, historie=historie,
        winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.15, "coverage_p10_p90": 0.79, "n_observaties": 500},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=30, versleuteld=False,
    )
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Organisatie B", slug="org-b", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_a, email="eigenaar-a@klant.nl", wachtwoord="wachtwoord-a", rol="eigenaar")
    maak_gebruiker(engine, organisatie_id=org_a, email="lid-a@klant.nl", wachtwoord="wachtwoord-a-lid", rol="lid")
    maak_gebruiker(engine, organisatie_id=org_b, email="eigenaar-b@klant.nl", wachtwoord="wachtwoord-b", rol="eigenaar")

    monkeypatch.setenv("MODEL_VERSION", versie)
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tenants_db_pad))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", "1000")
    monkeypatch.setenv("SESSIE_COOKIE_SECURE", "false")

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return TestClient(module.app), engine


def _inloggen(client, email, wachtwoord):
    resp = client.post("/login", json={"email": email, "wachtwoord": wachtwoord})
    assert resp.status_code == 200, resp.text


def test_eigenaar_kan_eigen_winkel_aanmaken(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["naam"] == "Webshop A"
    assert data["heeft_verkoopdata"] is False
    assert data["gemiddelde_omzet_per_stuk"] is None


def test_lid_kan_geen_eigen_winkel_aanmaken(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})

    assert resp.status_code == 403


def test_dubbele_naam_geeft_409(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})

    resp = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})

    assert resp.status_code == 409


def test_lid_kan_eigen_winkels_lijst_lezen(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})
    client.post("/logout")
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.get("/organisatie/eigen-winkels")

    assert resp.status_code == 200
    assert [w["naam"] for w in resp.json()] == ["Webshop A"]


def test_eigen_winkels_lijst_toont_alleen_eigen_organisatie(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"})
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.get("/organisatie/eigen-winkels")

    assert resp.json() == []


def test_hernoemen_werkt(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]

    resp = client.patch(f"/organisatie/eigen-winkels/{winkel_id}", json={"naam": "Webshop B"})

    assert resp.status_code == 200
    assert resp.json()["naam"] == "Webshop B"


def test_hernoemen_andermans_winkel_geeft_404(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.patch(f"/organisatie/eigen-winkels/{winkel_id}", json={"naam": "Overname"})

    assert resp.status_code == 404


def test_verwijderen_werkt(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]

    resp = client.delete(f"/organisatie/eigen-winkels/{winkel_id}")

    assert resp.status_code == 204
    assert client.get("/organisatie/eigen-winkels").json() == []


def test_verwijderen_andermans_winkel_geeft_404(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.delete(f"/organisatie/eigen-winkels/{winkel_id}")

    assert resp.status_code == 404


def test_prijs_instellen_werkt(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]

    resp = client.put(f"/organisatie/eigen-winkels/{winkel_id}/instellingen", json={"gemiddelde_omzet_per_stuk": 24.5})

    assert resp.status_code == 200
    assert resp.json()["gemiddelde_omzet_per_stuk"] == 24.5


def test_prijs_instellen_andermans_winkel_geeft_404(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.put(f"/organisatie/eigen-winkels/{winkel_id}/instellingen", json={"gemiddelde_omzet_per_stuk": 24.5})

    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_eigen_winkels_endpoint.py -v`
Expected: FAIL — all routes 404 (don't exist yet).

- [ ] **Step 3: Add the endpoints to `serving/app.py`**

Add `from db import eigen_winkel_instellingen as db_eigen_winkel_instellingen` and `from db import eigen_winkels as db_eigen_winkels` to the `from db import ...` block (alphabetical, near the other `db import` lines ~24-33). Add `from serving.prijs_per_stuk import bereken_gemiddelde_prijs_per_stuk` near the other `serving.*` imports. Add `EigenWinkelAanmakenVerzoek`, `EigenWinkelHernoemenVerzoek`, `EigenWinkelInstellingenVerzoek`, `EigenWinkelResponse` to the `from serving.schemas import (...)` block, and remove `OrganisatieInstellingenResponse`/`OrganisatieInstellingenVerzoek` from it.

Add a helper (used by every endpoint below and by Task 9's endpoints) right above the first new route, and the four/five CRUD routes themselves — place all of this where `GET`/`PUT /organisatie/instellingen` currently live (Task 9 removes those two routes from this exact spot):

```python
def _bouw_eigen_winkel_response(eigen_winkel_id: int, naam: str, heeft_verkoopdata: bool) -> EigenWinkelResponse:
    handmatige_prijs = db_eigen_winkel_instellingen.haal_prijs(tenants_db, eigen_winkel_id=eigen_winkel_id)
    automatische_prijs = bereken_gemiddelde_prijs_per_stuk(
        db_verkoopdata.haal_verkoopdata(tenants_db, eigen_winkel_id=eigen_winkel_id),
        db_product_verkoopdata.haal_product_verkoopdata(tenants_db, eigen_winkel_id=eigen_winkel_id),
    )
    return EigenWinkelResponse(
        id=eigen_winkel_id, naam=naam, heeft_verkoopdata=heeft_verkoopdata,
        gemiddelde_omzet_per_stuk=handmatige_prijs, automatische_prijs_per_stuk=automatische_prijs,
    )


@app.post("/organisatie/eigen-winkels", response_model=EigenWinkelResponse, status_code=201)
def eigen_winkel_aanmaken(
    verzoek: EigenWinkelAanmakenVerzoek, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)
) -> EigenWinkelResponse:
    try:
        winkel_id = db_eigen_winkels.maak_eigen_winkel(tenants_db, organisatie_id=eigenaar.organisatie_id, naam=verzoek.naam)
    except IntegrityError:
        raise HTTPException(status_code=409, detail=f"Eigen winkel {verzoek.naam!r} bestaat al.")
    return _bouw_eigen_winkel_response(winkel_id, verzoek.naam, heeft_verkoopdata=False)


@app.get("/organisatie/eigen-winkels", response_model=list[EigenWinkelResponse])
def eigen_winkels_lijst(gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)) -> list[EigenWinkelResponse]:
    winkels = db_eigen_winkels.lijst_eigen_winkels(tenants_db, organisatie_id=gebruiker.organisatie_id)
    return [_bouw_eigen_winkel_response(w["id"], w["naam"], w["heeft_verkoopdata"]) for w in winkels]


@app.patch("/organisatie/eigen-winkels/{eigen_winkel_id}", response_model=EigenWinkelResponse)
def eigen_winkel_hernoemen(
    eigen_winkel_id: int, verzoek: EigenWinkelHernoemenVerzoek,
    eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar),
) -> EigenWinkelResponse:
    try:
        gelukt = db_eigen_winkels.hernoem_eigen_winkel(
            tenants_db, organisatie_id=eigenaar.organisatie_id, eigen_winkel_id=eigen_winkel_id, nieuwe_naam=verzoek.naam
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail=f"Eigen winkel {verzoek.naam!r} bestaat al.")
    if not gelukt:
        raise HTTPException(status_code=404, detail=f"Onbekende eigen winkel: {eigen_winkel_id}")
    winkels = db_eigen_winkels.lijst_eigen_winkels(tenants_db, organisatie_id=eigenaar.organisatie_id)
    winkel = next(w for w in winkels if w["id"] == eigen_winkel_id)
    return _bouw_eigen_winkel_response(winkel["id"], winkel["naam"], winkel["heeft_verkoopdata"])


@app.delete("/organisatie/eigen-winkels/{eigen_winkel_id}", status_code=204)
def eigen_winkel_verwijderen(
    eigen_winkel_id: int, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)
) -> None:
    gelukt = db_eigen_winkels.verwijder_eigen_winkel(
        tenants_db, organisatie_id=eigenaar.organisatie_id, eigen_winkel_id=eigen_winkel_id
    )
    if not gelukt:
        raise HTTPException(status_code=404, detail=f"Onbekende eigen winkel: {eigen_winkel_id}")


@app.put("/organisatie/eigen-winkels/{eigen_winkel_id}/instellingen", response_model=EigenWinkelResponse)
def eigen_winkel_instellingen_instellen(
    eigen_winkel_id: int, verzoek: EigenWinkelInstellingenVerzoek,
    eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar),
) -> EigenWinkelResponse:
    winkels = db_eigen_winkels.lijst_eigen_winkels(tenants_db, organisatie_id=eigenaar.organisatie_id)
    winkel = next((w for w in winkels if w["id"] == eigen_winkel_id), None)
    if winkel is None:
        raise HTTPException(status_code=404, detail=f"Onbekende eigen winkel: {eigen_winkel_id}")
    db_eigen_winkel_instellingen.stel_prijs_in(
        tenants_db, eigen_winkel_id=eigen_winkel_id, bedrag=verzoek.gemiddelde_omzet_per_stuk
    )
    return _bouw_eigen_winkel_response(winkel["id"], winkel["naam"], winkel["heeft_verkoopdata"])
```

Note the `.first()`/`next(w for w in winkels if w["id"] == eigen_winkel_id)` re-fetch-list-then-find pattern above intentionally reuses `lijst_eigen_winkels()` (which already enforces `organisatie_id`) rather than adding a new single-row `db/eigen_winkels.py` lookup function — keeps the module's public surface to exactly the four functions Task 2 defined.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_eigen_winkels_endpoint.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add serving/app.py tests/test_eigen_winkels_endpoint.py
git commit -m "forecasting: voeg CRUD-endpoints toe voor /organisatie/eigen-winkels"
```

---

### Task 9: `serving/app.py` — verkoopdata-endpoints scopen op `eigen_winkel_id`, `/organisatie/instellingen` verwijderen

**Files:**
- Modify: `serving/app.py`
- Test: `tests/test_verkoopdata_endpoint.py`
- Test: `tests/test_eigen_voorspelling_endpoint.py`
- Test: `tests/test_organisatie_instellingen_endpoint.py` (delete this file — endpoint no longer exists)

**Interfaces:**
- Consumes: everything from Task 8.
- Produces: `POST`/`GET /organisatie/verkoopdata` and `POST /organisatie/product-verkoopdata` and `GET /organisatie/herbestel-advies-per-product` and `GET /organisatie/eigen-voorspelling` all require `eigen_winkel_id` (query param for GET, form field for POST) and validate it belongs to the caller's organisation.

- [ ] **Step 1: Delete the obsolete test file, update the others**

Delete `tests/test_organisatie_instellingen_endpoint.py` entirely (its endpoint is gone — its test cases are already covered by Task 8's `test_prijs_instellen_werkt`/`test_prijs_instellen_andermans_winkel_geeft_404`).

In `tests/test_verkoopdata_endpoint.py` and `tests/test_eigen_voorspelling_endpoint.py`: every `client.post("/organisatie/verkoopdata", files=...)` becomes `client.post("/organisatie/verkoopdata", files=..., data={"eigen_winkel_id": str(winkel_id)})`, and every `client.get("/organisatie/verkoopdata")`/`client.get("/organisatie/eigen-voorspelling")` becomes `client.get("/organisatie/verkoopdata", params={"eigen_winkel_id": winkel_id})`/`client.get("/organisatie/eigen-voorspelling", params={"eigen_winkel_id": winkel_id})` — with `winkel_id` created via `client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]` at the top of each test (after logging in as the eigenaar). Add one new test to `tests/test_verkoopdata_endpoint.py`:

```python
def test_verkoopdata_uploaden_zonder_eigen_winkel_id_faalt(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.post(
        "/organisatie/verkoopdata", files={"bestand": ("data.csv", "datum,omzet\n2026-01-01,100\n", "text/csv")}
    )

    assert resp.status_code == 422


def test_verkoopdata_uploaden_andermans_eigen_winkel_id_geeft_404(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = client.post("/organisatie/eigen-winkels", json={"naam": "Webshop A"}).json()["id"]
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.post(
        "/organisatie/verkoopdata",
        files={"bestand": ("data.csv", "datum,omzet\n2026-01-01,100\n", "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    assert resp.status_code == 404
```

Apply the same `eigen_winkel_id` parameterisation to any `/organisatie/product-verkoopdata` and `/organisatie/herbestel-advies-per-product` calls in `tests/test_product_verkoopdata_endpoint.py` (grep the file for those two paths first — same mechanical change as above, form field for POST, query param for GET).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_verkoopdata_endpoint.py tests/test_eigen_voorspelling_endpoint.py tests/test_product_verkoopdata_endpoint.py -v`
Expected: FAIL — endpoints don't yet accept/require `eigen_winkel_id`.

- [ ] **Step 3: Edit the four endpoints in `serving/app.py`**

Remove the `GET`/`PUT /organisatie/instellingen` routes entirely (currently lines 583-601 — replaced by Task 8's `/organisatie/eigen-winkels/*` routes already added at that location).

Add a shared ownership-check helper right above `verkoopdata_lezen` (reused by all four endpoints below):

```python
def _vereis_eigen_winkel(organisatie_id: int, eigen_winkel_id: int) -> None:
    winkels = db_eigen_winkels.lijst_eigen_winkels(tenants_db, organisatie_id=organisatie_id)
    if not any(w["id"] == eigen_winkel_id for w in winkels):
        raise HTTPException(status_code=404, detail=f"Onbekende eigen winkel: {eigen_winkel_id}")
```

Replace `verkoopdata_lezen`/`verkoopdata_uploaden` (currently lines 604-622):

```python
@app.get("/organisatie/verkoopdata", response_model=VerkoopdataResponse)
def verkoopdata_lezen(
    eigen_winkel_id: int = Query(...), gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)
) -> VerkoopdataResponse:
    _vereis_eigen_winkel(gebruiker.organisatie_id, eigen_winkel_id)
    rijen = db_verkoopdata.haal_verkoopdata(tenants_db, eigen_winkel_id=eigen_winkel_id)
    return VerkoopdataResponse(rijen=[VerkoopdataRij(**r) for r in rijen])


@app.post("/organisatie/verkoopdata", response_model=VerkoopdataUploadResponse)
def verkoopdata_uploaden(
    bestand: UploadFile, eigen_winkel_id: int = Form(...),
    eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar),
) -> VerkoopdataUploadResponse:
    _vereis_eigen_winkel(eigenaar.organisatie_id, eigen_winkel_id)
    inhoud = bestand.file.read().decode("utf-8", errors="replace")
    try:
        rijen = parse_verkoopdata_csv(inhoud)
    except OngeldigeVerkoopdata as e:
        raise HTTPException(status_code=422, detail=str(e))
    db_verkoopdata.vervang_verkoopdata(tenants_db, eigen_winkel_id=eigen_winkel_id, rijen=rijen)
    return VerkoopdataUploadResponse(aantal_rijen=len(rijen))
```

Add `Form` to the `from fastapi import (...)` line at the top of the file (it currently imports `Depends, FastAPI, HTTPException, Query, Request, Response, Security, UploadFile` — add `Form` alphabetically).

Replace `eigen_voorspelling_lezen` (currently lines 625-645) — same shape, adds the `eigen_winkel_id` param, `_vereis_eigen_winkel` check, and now sources the price via the auto-calc-then-manual-fallback order from the spec instead of `db_organisaties.haal_gemiddelde_omzet_per_stuk`:

```python
@app.get("/organisatie/eigen-voorspelling", response_model=EigenVoorspellingResponse)
def eigen_voorspelling_lezen(
    eigen_winkel_id: int = Query(...), horizon_dagen: int = Query(7, gt=0),
    gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie),
) -> EigenVoorspellingResponse:
    _vereis_eigen_winkel(gebruiker.organisatie_id, eigen_winkel_id)
    rijen = db_verkoopdata.haal_verkoopdata(tenants_db, eigen_winkel_id=eigen_winkel_id)
    if len(rijen) < MINIMUM_DAGEN:
        return EigenVoorspellingResponse(beschikbaar=False, dagen_verzameld=len(rijen), dagen_nodig=MINIMUM_DAGEN)

    resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=horizon_dagen, vanaf=date.today())
    product_rijen = db_product_verkoopdata.haal_product_verkoopdata(tenants_db, eigen_winkel_id=eigen_winkel_id)
    prijs = bereken_gemiddelde_prijs_per_stuk(rijen, product_rijen)
    if prijs is None:
        prijs = db_eigen_winkel_instellingen.haal_prijs(tenants_db, eigen_winkel_id=eigen_winkel_id)
    advies = herbestel_advies(resultaat["totaal_p10"], resultaat["totaal_p50"], resultaat["totaal_p90"], prijs)
    return EigenVoorspellingResponse(
        beschikbaar=True, dagen_verzameld=len(rijen), dagen_nodig=MINIMUM_DAGEN,
        voorspellingen=[EigenVoorspellingDag(**v) for v in resultaat["voorspellingen"]],
        totaal_p10=resultaat["totaal_p10"], totaal_p50=resultaat["totaal_p50"], totaal_p90=resultaat["totaal_p90"],
        herbestel_advies=HerbestelAdvies(**advies) if advies else None,
    )
```

Replace `product_verkoopdata_uploaden` (currently lines 648-666):

```python
@app.post("/organisatie/product-verkoopdata", response_model=ProductVerkoopdataUploadResponse)
def product_verkoopdata_uploaden(
    bestand: UploadFile, eigen_winkel_id: int = Form(...),
    eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar),
) -> ProductVerkoopdataUploadResponse:
    # Herbestel-advies per product is een premium-functie (zelfde reden
    # als self-serve API-keys hierboven) — nooit beschikbaar tijdens de
    # proefperiode.
    if db_organisaties.is_in_proefperiode(tenants_db, eigenaar.organisatie_id):
        raise HTTPException(
            status_code=403,
            detail="Herbestel-advies per product is een premium-functie, niet beschikbaar in je proefperiode.",
        )
    _vereis_eigen_winkel(eigenaar.organisatie_id, eigen_winkel_id)
    inhoud = bestand.file.read().decode("utf-8", errors="replace")
    try:
        rijen = parse_product_verkoopdata_csv(inhoud)
    except OngeldigeProductVerkoopdata as e:
        raise HTTPException(status_code=422, detail=str(e))
    db_product_verkoopdata.vervang_product_verkoopdata(tenants_db, eigen_winkel_id=eigen_winkel_id, rijen=rijen)
    return ProductVerkoopdataUploadResponse(aantal_rijen=len(rijen))
```

Replace `herbestel_advies_per_product_lezen` (currently lines 669-682):

```python
@app.get("/organisatie/herbestel-advies-per-product", response_model=ProductHerbestelAdviesResponse)
def herbestel_advies_per_product_lezen(
    eigen_winkel_id: int = Query(...), horizon_dagen: int = Query(7, gt=0),
    gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie),
) -> ProductHerbestelAdviesResponse:
    """Leesbaar voor elke ingelogde gebruiker, net als /organisatie/
    eigen-voorspelling — alleen het uploaden is eigenaar-only."""
    if db_organisaties.is_in_proefperiode(tenants_db, gebruiker.organisatie_id):
        raise HTTPException(
            status_code=403,
            detail="Herbestel-advies per product is een premium-functie, niet beschikbaar in je proefperiode.",
        )
    _vereis_eigen_winkel(gebruiker.organisatie_id, eigen_winkel_id)
    rijen = db_product_verkoopdata.haal_product_verkoopdata(tenants_db, eigen_winkel_id=eigen_winkel_id)
    items = bereken_herbestel_advies_per_product(rijen, horizon_dagen=horizon_dagen, vanaf=date.today())
    return ProductHerbestelAdviesResponse(items=items)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_verkoopdata_endpoint.py tests/test_eigen_voorspelling_endpoint.py tests/test_product_verkoopdata_endpoint.py tests/test_eigen_winkels_endpoint.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend test suite**

Run: `pytest -q` (excluding the pre-existing local xgboost/libomp collection errors documented in Global Constraints if they resurface — those are environment issues unrelated to this change; if they block collection, run `pytest -q --ignore=<the affected files>` and note it, don't attempt to fix them here).
Expected: everything except the known-environment-broken files passes.

- [ ] **Step 6: Commit**

```bash
git add serving/app.py tests/test_verkoopdata_endpoint.py tests/test_eigen_voorspelling_endpoint.py tests/test_product_verkoopdata_endpoint.py
git rm tests/test_organisatie_instellingen_endpoint.py
git commit -m "forecasting: vereis eigen_winkel_id op verkoopdata-endpoints, verwijder /organisatie/instellingen"
```

---

### Task 10: `serving/herbestel_email.py` — per eigen winkel itereren

**Files:**
- Modify: `serving/herbestel_email.py`
- Test: `tests/test_herbestel_email.py`

**Interfaces:**
- Consumes: `db.eigen_winkels.lijst_eigen_winkels` (Task 2), `db.verkoopdata.haal_verkoopdata`/`db.product_verkoopdata.haal_product_verkoopdata` (Task 4), `serving.prijs_per_stuk.bereken_gemiddelde_prijs_per_stuk` (Task 6), `db.eigen_winkel_instellingen.haal_prijs` (Task 3).
- Produces: `bouw_email_inhoud(organisatie_naam: str, gedeeld_model_forecast: dict | None, eigen_winkel_secties: list[dict]) -> tuple[str, str]` (signature changes — was `totaal_p10, totaal_p50, totaal_p90, advies`). Each item in `eigen_winkel_secties`: `{"naam": str, "totaal_p10": float, "totaal_p50": float, "totaal_p90": float, "advies": dict | None}`.

- [ ] **Step 1: Update the failing tests**

Read `tests/test_herbestel_email.py` fully first — it has tests for `bouw_email_inhoud()` directly and for `verstuur_wekelijkse_herbestel_mails()` end-to-end with a fake mail sender. Update every call/fixture that currently uploads org-wide eigen verkoopdata (via `db_verkoopdata.vervang_verkoopdata(engine, organisatie_id=org_id, ...)`) to first create an eigen winkel (`db_eigen_winkels.maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")`) and upload against `eigen_winkel_id=winkel_id` instead. Update assertions on the built email text: instead of asserting the omzet/advies numbers appear directly in the body, assert the eigen winkel's *naam* ("Webshop A") appears as a section header, followed by its numbers. Update any direct call to `bouw_email_inhoud(...)` to match the new signature above (pass a list with one dict instead of four scalar args for the eigen-data case; pass `None`/`[]` for whichever branch isn't under test in each specific test).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_herbestel_email.py -v`
Expected: FAIL — `bouw_email_inhoud()` signature mismatch, `_verzamel_forecast_via_eigen_data()` still calls `db_verkoopdata.haal_verkoopdata(engine, organisatie_id=...)`.

- [ ] **Step 3: Rewrite `serving/herbestel_email.py`**

Add `from db import eigen_winkel_instellingen as db_eigen_winkel_instellingen`, `from db import eigen_winkels as db_eigen_winkels`, `from db import product_verkoopdata as db_product_verkoopdata`, `from serving.prijs_per_stuk import bereken_gemiddelde_prijs_per_stuk` to the imports.

Replace `_verzamel_forecast_via_eigen_data()` (currently lines 64-72) with a function that returns one entry per eigen winkel instead of one aggregate:

```python
def _verzamel_secties_via_eigen_winkels(engine, organisatie_id: int, start_datum: date) -> list[dict]:
    secties = []
    for winkel in db_eigen_winkels.lijst_eigen_winkels(engine, organisatie_id=organisatie_id):
        rijen = db_verkoopdata.haal_verkoopdata(engine, eigen_winkel_id=winkel["id"])
        resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=HORIZON_DAGEN, vanaf=start_datum)
        if resultaat is None:
            continue
        product_rijen = db_product_verkoopdata.haal_product_verkoopdata(engine, eigen_winkel_id=winkel["id"])
        prijs = bereken_gemiddelde_prijs_per_stuk(rijen, product_rijen)
        if prijs is None:
            prijs = db_eigen_winkel_instellingen.haal_prijs(engine, eigen_winkel_id=winkel["id"])
        advies = herbestel_advies(resultaat["totaal_p10"], resultaat["totaal_p50"], resultaat["totaal_p90"], prijs)
        secties.append({
            "naam": winkel["naam"], "totaal_p10": resultaat["totaal_p10"],
            "totaal_p50": resultaat["totaal_p50"], "totaal_p90": resultaat["totaal_p90"], "advies": advies,
        })
    return secties
```

Replace `bouw_email_inhoud()` (currently lines 75-95) — now takes the gedeeld-model totals (unchanged shape, still one aggregate — that branch is untouched by this feature) plus the new per-eigen-winkel sections list, and renders one paragraph block per eigen winkel instead of a single "kern_alinea":

```python
def bouw_email_inhoud(
    organisatie_naam: str, gedeeld_model_forecast: Optional[dict], eigen_winkel_secties: list[dict]
) -> tuple[str, str]:
    onderwerp = f"Wekelijkse voorspelling voor {organisatie_naam}"
    blokken = []
    if gedeeld_model_forecast:
        p10, p50, p90 = (gedeeld_model_forecast[k] for k in ("totaal_p10", "totaal_p50", "totaal_p90"))
        blokken.append(
            (f"Verwachte omzet komende {HORIZON_DAGEN} dagen: ongeveer €{p50:,.0f} "
             f"(bandbreedte €{p10:,.0f} tot €{p90:,.0f}).").replace(",", ".")
        )
    for sectie in eigen_winkel_secties:
        p10, p50, p90 = sectie["totaal_p10"], sectie["totaal_p50"], sectie["totaal_p90"]
        kop = f"{sectie['naam']}:"
        if sectie["advies"]:
            regel = (
                f"Bestel deze week ongeveer {sectie['advies']['stuks_p50']} stuks bij. Houd rekening met pieken "
                f"tot {sectie['advies']['stuks_p90']} stuks bij drukte, en met minder verkoop tot "
                f"{sectie['advies']['stuks_p10']} stuks als het rustiger is dan verwacht."
            )
        else:
            regel = (
                f"Verwachte omzet komende {HORIZON_DAGEN} dagen: ongeveer €{p50:,.0f} "
                f"(bandbreedte €{p10:,.0f} tot €{p90:,.0f})."
            ).replace(",", ".")
        blokken.append(f"{kop}\n{regel}")
    tekst = (
        f"Hallo,\n\nDit is je wekelijkse update van KwantIQ voor {organisatie_naam}.\n\n"
        + "\n\n".join(blokken) + "\n\nLog in op je dashboard voor de details.\n"
    )
    return onderwerp, tekst
```

Update `verstuur_wekelijkse_herbestel_mails()` (currently lines 98-138): replace the `forecast = _verzamel_forecast_via_gedeeld_model(...); if forecast is None: forecast = _verzamel_forecast_via_eigen_data(...); if forecast is None: continue` block with:

```python
        gedeeld_model_forecast = _verzamel_forecast_via_gedeeld_model(modellen, historie, winkel_metadata, winkels, start_datum)
        eigen_winkel_secties = _verzamel_secties_via_eigen_winkels(engine, org.id, start_datum)
        if gedeeld_model_forecast is None and not eigen_winkel_secties:
            continue
```

and replace the `prijs = db_organisaties.haal_gemiddelde_omzet_per_stuk(...); advies = herbestel_advies(...); onderwerp, tekst = bouw_email_inhoud(...)` block with:

```python
        onderwerp, tekst = bouw_email_inhoud(org.naam, gedeeld_model_forecast, eigen_winkel_secties)
```

Remove the now-unused `db_organisaties` import if nothing else in the file uses it (check — `db_organisaties.lijst_actieve_organisaties` is still called in the surrounding loop, so the import stays).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_herbestel_email.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add serving/herbestel_email.py tests/test_herbestel_email.py
git commit -m "forecasting: wekelijkse herbestel-mail itereert per eigen winkel i.p.v. org-breed"
```

---

### Task 11: `dashboard/onboarding.js` — checklist via eigen-winkels-lijst

**Files:**
- Modify: `dashboard/onboarding.js`

**Interfaces:**
- Consumes: `GET /organisatie/eigen-winkels` (Task 8) response shape `{id, naam, heeft_verkoopdata, gemiddelde_omzet_per_stuk, automatische_prijs_per_stuk}[]`.

No automated test — this file has none today (matches the codebase's existing dashboard-JS testing posture, see Global Constraints/spec Testing section). Verified live in Task 15.

- [ ] **Step 1: Edit `haalOnboardingStatus()`**

Replace the current body (lines 37-49):

```javascript
async function haalOnboardingStatus() {
  const resp = await fetch(`${ONBOARDING_API_BASIS}/organisatie/eigen-winkels`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error("Kon onboarding-status niet ophalen");
  const winkels = await resp.json();
  return {
    verkoopdataGeupload: winkels.some((w) => w.heeft_verkoopdata),
    prijsIngesteld: winkels.some((w) => w.gemiddelde_omzet_per_stuk !== null || w.automatische_prijs_per_stuk !== null),
  };
}
```

The rest of `onboarding.js` (`toonOnboardingChecklist()` and everything below it) consumes only the `{verkoopdataGeupload, prijsIngesteld}` shape this function returns, which is unchanged — no other edits needed in this file.

- [ ] **Step 2: Sanity-check with a quick manual trace**

No test to run automatically; instead, re-read the edited function once against `serving/app.py`'s `GET /organisatie/eigen-winkels` response model (Task 8) to confirm field names match exactly (`heeft_verkoopdata`, `gemiddelde_omzet_per_stuk`, `automatische_prijs_per_stuk`) — a silent typo here would only surface as a checklist that never completes, not a crash. Full behavioural verification happens live in Task 15.

- [ ] **Step 3: Commit**

```bash
git add dashboard/onboarding.js
git commit -m "forecasting: onboarding-checklist leest eigen-winkels-lijst i.p.v. org-brede endpoints"
```

---

### Task 12: `dashboard/team.html` + `account.js` — "Eigen winkels"-beheerkaart

**Files:**
- Modify: `dashboard/team.html`
- Modify: `dashboard/account.js`

**Interfaces:**
- Consumes: the five `/organisatie/eigen-winkels*` endpoints (Task 8).
- Produces: a `laadEigenWinkels()` module-level array kept in sync with the server, and a `verversEigenWinkelsKaart()` function that both Task 12 and Task 13 call after any create/rename/delete/upload.

No automated test — matches the existing dashboard-JS testing posture. Verified live in Task 15.

- [ ] **Step 1: Replace the `herbestel-kaart` block in `dashboard/team.html`**

Delete the entire `<div class="kaart" id="herbestel-kaart" hidden>...</div>` block (currently lines 105-120) — the price field moves into the new per-winkel card below.

In its place, add:

```html
<div class="kaart" id="eigen-winkels-kaart" hidden>
  <p class="sub" style="margin:0;">
    Eigen winkels groeperen je geüploade verkoopdata (webshop, marktkraam, ...) elk apart — geen koppeling met
    het gedeelde voorspelmodel, puur een naam om je eigen CSV-uploads onder te ordenen.
  </p>
  <form id="eigen-winkel-aanmaken-form" style="display:flex; gap:14px; align-items:end; flex-wrap:wrap;">
    <div class="veld">
      <label for="eigen-winkel-naam">Naam</label>
      <input type="text" id="eigen-winkel-naam" required>
    </div>
    <button type="submit" class="btn" id="eigen-winkel-aanmaken-knop">Aanmaken</button>
  </form>
  <p class="fout" id="eigen-winkel-aanmaken-fout" hidden></p>
  <div class="teamlijst" id="eigen-winkels-lijst"></div>
  <p class="sub" id="eigen-winkels-leeg" hidden style="margin:16px 0 0;">
    Nog geen eigen winkel — maak er hierboven één aan om verkoopdata te kunnen uploaden.
  </p>
</div>
```

- [ ] **Step 2: Add the fetch functions to `dashboard/account.js`**

Remove `haalOrganisatieInstellingen()`, `stelGemiddeldeOmzetPerStukIn()`, and `initHerbestelForm()` entirely (currently lines 374-425) — replaced below.

Add, in their place:

```javascript
async function haalEigenWinkels() {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-winkels`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon eigen winkels niet ophalen (${resp.status})`);
  return resp.json();
}

async function maakEigenWinkel(naam) {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-winkels`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ naam }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Aanmaken mislukt (${resp.status})`);
  }
  return resp.json();
}

async function hernoemEigenWinkel(id, naam) {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-winkels/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ naam }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Hernoemen mislukt (${resp.status})`);
  }
  return resp.json();
}

async function verwijderEigenWinkel(id) {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-winkels/${id}`, { method: "DELETE", credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Verwijderen mislukt (${resp.status})`);
}

async function stelEigenWinkelPrijsIn(id, bedrag) {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-winkels/${id}/instellingen`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ gemiddelde_omzet_per_stuk: bedrag }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Opslaan mislukt (${resp.status})`);
  }
  return resp.json();
}
```

- [ ] **Step 3: Add the row-rendering + list-refresh functions**

Add, mirroring `maakApiKeyEl()`/`verversApiKeysLijst()` (`dashboard/account.js:602-641`):

```javascript
function maakEigenWinkelEl(winkel, opNaamGewijzigd) {
  const rij = document.createElement("div");
  rij.className = "teamlid";

  const naam = document.createElement("span");
  naam.className = "email";
  naam.textContent = winkel.naam;

  const rechts = document.createElement("span");
  rechts.className = "rechts";

  const prijsVeld = document.createElement("input");
  prijsVeld.type = "number";
  prijsVeld.min = "0.01";
  prijsVeld.step = "0.01";
  prijsVeld.style.width = "90px";
  prijsVeld.placeholder = winkel.automatische_prijs_per_stuk !== null
    ? `auto: €${winkel.automatische_prijs_per_stuk.toFixed(2)}` : "prijs/stuk";
  if (winkel.gemiddelde_omzet_per_stuk !== null) prijsVeld.value = winkel.gemiddelde_omzet_per_stuk;
  const prijsKnop = document.createElement("button");
  prijsKnop.type = "button";
  prijsKnop.className = "btn zacht";
  prijsKnop.textContent = "Opslaan";
  prijsKnop.addEventListener("click", async () => {
    prijsKnop.disabled = true;
    try {
      await stelEigenWinkelPrijsIn(winkel.id, Number(prijsVeld.value));
      await opNaamGewijzigd();
    } catch (e) {
      toonFout("eigen-winkel-aanmaken-fout", e.message);
    } finally {
      prijsKnop.disabled = false;
    }
  });

  const hernoemKnop = document.createElement("button");
  hernoemKnop.type = "button";
  hernoemKnop.className = "btn zacht";
  hernoemKnop.textContent = "Hernoemen";
  hernoemKnop.addEventListener("click", async () => {
    const nieuweNaam = window.prompt("Nieuwe naam:", winkel.naam);
    if (!nieuweNaam || nieuweNaam === winkel.naam) return;
    try {
      await hernoemEigenWinkel(winkel.id, nieuweNaam);
      await opNaamGewijzigd();
    } catch (e) {
      toonFout("eigen-winkel-aanmaken-fout", e.message);
    }
  });

  const verwijderKnop = document.createElement("button");
  verwijderKnop.type = "button";
  verwijderKnop.className = "btn zacht";
  verwijderKnop.textContent = "Verwijderen";
  verwijderKnop.addEventListener("click", async () => {
    if (!window.confirm(`"${winkel.naam}" en al zijn geüploade verkoopdata verwijderen? Dit kan niet ongedaan worden gemaakt.`)) return;
    verwijderKnop.disabled = true;
    try {
      await verwijderEigenWinkel(winkel.id);
      await opNaamGewijzigd();
    } catch (e) {
      toonFout("eigen-winkel-aanmaken-fout", e.message);
      verwijderKnop.disabled = false;
    }
  });

  rechts.append(prijsVeld, prijsKnop, hernoemKnop, verwijderKnop);
  rij.append(naam, rechts);
  return rij;
}

let alleEigenWinkels = [];

async function verversEigenWinkelsKaart() {
  alleEigenWinkels = await haalEigenWinkels();
  const lijstEl = document.getElementById("eigen-winkels-lijst");
  lijstEl.replaceChildren(...alleEigenWinkels.map((w) => maakEigenWinkelEl(w, verversEigenWinkelsKaart)));
  document.getElementById("eigen-winkels-leeg").hidden = alleEigenWinkels.length > 0;
  vulEigenWinkelSelects(alleEigenWinkels);
}
```

`vulEigenWinkelSelects()` is defined in Task 13 (it populates the two `<select>` dropdowns Task 13 adds) — leave it as a forward reference for now, Task 13 completes the file.

- [ ] **Step 4: Wire the create form and card visibility**

Add, mirroring `initNieuweKeyForm()`:

```javascript
function initEigenWinkelAanmakenForm() {
  const form = document.getElementById("eigen-winkel-aanmaken-form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("eigen-winkel-aanmaken-knop");
    knop.disabled = true;
    toonFout("eigen-winkel-aanmaken-fout", "");
    try {
      const naamVeld = document.getElementById("eigen-winkel-naam");
      await maakEigenWinkel(naamVeld.value);
      naamVeld.value = "";
      await verversEigenWinkelsKaart();
    } catch (e) {
      toonFout("eigen-winkel-aanmaken-fout", e.message);
    } finally {
      knop.disabled = false;
    }
  });
}
```

In `initTeamPagina()` (`dashboard/account.js:771-863`), inside the existing `if (kanBeheren) { ... }` block (lines 810-830), remove the three lines that reference `herbestel-kaart`/`haalOrganisatieInstellingen`/`initHerbestelForm` (lines 812, 815-822 shown earlier), and add in their place:

```javascript
    document.getElementById("eigen-winkels-kaart").hidden = false;
    try {
      await verversEigenWinkelsKaart();
    } catch (e) {
      toonFout("fout", e.message);
    }
    initEigenWinkelAanmakenForm();
```

- [ ] **Step 5: Manual verification (no automated test for this task)**

Deferred to Task 15's live browser check — this task alone doesn't produce a runnable increment without Task 13's `vulEigenWinkelSelects()`, so don't attempt to load the page yet.

- [ ] **Step 6: Commit**

```bash
git add dashboard/team.html dashboard/account.js
git commit -m "forecasting: voeg 'Eigen winkels'-beheerkaart toe aan team.html"
```

---

### Task 13: `dashboard/team.html` + `account.js` — winkel-keuze op de twee upload-kaarten

**Files:**
- Modify: `dashboard/team.html`
- Modify: `dashboard/account.js`

**Interfaces:**
- Consumes: `alleEigenWinkels` (Task 12), `verversEigenWinkelsKaart()` (Task 12).
- Produces: `vulEigenWinkelSelects(winkels)` (referenced by Task 12's `verversEigenWinkelsKaart()`).

- [ ] **Step 1: Add `<select>` elements to both upload forms in `dashboard/team.html`**

In the `verkoopdata-form` (currently lines 127-133), add a select before the file field:

```html
<form id="verkoopdata-form" style="display:flex; gap:14px; align-items:end; flex-wrap:wrap;">
  <div class="veld">
    <label for="verkoopdata-eigen-winkel">Eigen winkel</label>
    <select id="verkoopdata-eigen-winkel" required></select>
  </div>
  <div class="veld">
    <label for="verkoopdata-bestand">CSV-bestand</label>
    <input type="file" id="verkoopdata-bestand" accept=".csv" required>
  </div>
  <button type="submit" class="btn" id="verkoopdata-knop">Uploaden</button>
</form>
```

Apply the identical change to `product-verkoopdata-form` (currently lines 154-160), using ids `product-verkoopdata-eigen-winkel` for its select.

- [ ] **Step 2: Update `dashboard/account.js`'s verkoopdata functions to use the selected winkel**

Replace `haalVerkoopdata()`/`uploadVerkoopdata()` (currently lines 427-446):

```javascript
async function haalVerkoopdata(eigenWinkelId) {
  const resp = await fetch(`${API_BASIS}/organisatie/verkoopdata?eigen_winkel_id=${eigenWinkelId}`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon verkoopdata niet ophalen (${resp.status})`);
  return resp.json();
}

async function uploadVerkoopdata(eigenWinkelId, bestand) {
  const formData = new FormData();
  formData.append("eigen_winkel_id", eigenWinkelId);
  formData.append("bestand", bestand);
  const resp = await fetch(`${API_BASIS}/organisatie/verkoopdata`, {
    method: "POST",
    credentials: "same-origin",
    body: formData,
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Uploaden mislukt (${resp.status})`);
  }
  return resp.json();
}
```

Replace `haalEigenVoorspelling()` (currently lines 504-508) the same way, adding `eigenWinkelId` as a parameter and `?eigen_winkel_id=${eigenWinkelId}` to the URL.

Replace `haalProductHerbestelAdvies()`/`uploadProductVerkoopdata()` (currently lines 679-698) the same way (`eigenWinkelId` param, query-param on GET, form field on POST).

Update `initVerkoopdataForm()` (currently lines 545-570): read the selected winkel from the new `<select>` and pass it through:

```javascript
function initVerkoopdataForm() {
  const form = document.getElementById("verkoopdata-form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("verkoopdata-knop");
    const bestandVeld = document.getElementById("verkoopdata-bestand");
    const eigenWinkelId = Number(document.getElementById("verkoopdata-eigen-winkel").value);
    knop.disabled = true;
    toonFout("verkoopdata-fout", "");
    document.getElementById("verkoopdata-melding").hidden = true;
    try {
      const bestand = bestandVeld.files[0];
      const resultaat = await uploadVerkoopdata(eigenWinkelId, bestand);
      const melding = document.getElementById("verkoopdata-melding");
      melding.textContent = `${resultaat.aantal_rijen} dagen geüpload.`;
      melding.hidden = false;
      bestandVeld.value = "";
      toonVerkoopdata((await haalVerkoopdata(eigenWinkelId)).rijen);
      toonEigenVoorspelling(await haalEigenVoorspelling(eigenWinkelId));
      await verversEigenWinkelsKaart();
    } catch (e) {
      toonFout("verkoopdata-fout", e.message);
    } finally {
      knop.disabled = false;
    }
  });
}
```

(`await verversEigenWinkelsKaart()` at the end refreshes the management card's `heeft_verkoopdata`/auto-price display after an upload — it re-populates the selects too, so re-select the just-used winkel afterward isn't needed since `vulEigenWinkelSelects` (Step 3 below) preserves the current selection by id when repopulating.)

Apply the identical `eigenWinkelId`-threading change to `initProductVerkoopdataForm()` (currently lines 723-747), using `product-verkoopdata-eigen-winkel` as the select id.

- [ ] **Step 3: Add `vulEigenWinkelSelects()` and wire select-change handlers**

Add to `dashboard/account.js` (near `verversEigenWinkelsKaart`):

```javascript
function vulEigenWinkelSelects(winkels) {
  for (const selectId of ["verkoopdata-eigen-winkel", "product-verkoopdata-eigen-winkel"]) {
    const select = document.getElementById(selectId);
    if (!select) continue;
    const huidige = select.value;
    select.replaceChildren(...winkels.map((w) => {
      const optie = document.createElement("option");
      optie.value = String(w.id);
      optie.textContent = w.naam;
      return optie;
    }));
    if (winkels.some((w) => String(w.id) === huidige)) select.value = huidige;
    select.disabled = winkels.length === 0;
  }
  const kanUploaden = winkels.length > 0;
  document.getElementById("verkoopdata-knop").disabled = !kanUploaden;
  document.getElementById("product-verkoopdata-knop").disabled = !kanUploaden;
}

async function toonVerkoopdataVoorSelectie() {
  const select = document.getElementById("verkoopdata-eigen-winkel");
  if (!select.value) {
    document.getElementById("verkoopdata-grafiek-wrap").hidden = true;
    document.getElementById("eigen-voorspelling-voortgang").hidden = true;
    document.getElementById("eigen-voorspelling-aanbeveling").hidden = true;
    return;
  }
  const eigenWinkelId = Number(select.value);
  toonVerkoopdata((await haalVerkoopdata(eigenWinkelId)).rijen);
  toonEigenVoorspelling(await haalEigenVoorspelling(eigenWinkelId));
}

async function toonProductAdviesVoorSelectie() {
  const select = document.getElementById("product-verkoopdata-eigen-winkel");
  if (!select.value) return;
  toonProductHerbestelAdvies((await haalProductHerbestelAdvies(Number(select.value))).items);
}
```

Register the change listeners once, in `initTeamPagina()` right after Task 12's `initEigenWinkelAanmakenForm()` call:

```javascript
    document.getElementById("verkoopdata-eigen-winkel").addEventListener("change", () => {
      toonVerkoopdataVoorSelectie().catch((e) => toonFout("fout", e.message));
    });
    document.getElementById("product-verkoopdata-eigen-winkel").addEventListener("change", () => {
      toonProductAdviesVoorSelectie().catch((e) => toonFout("fout", e.message));
    });
```

- [ ] **Step 4: Update the rest of `initTeamPagina()`'s verkoopdata/product-verkoopdata sections**

Replace the verkoopdata block (currently lines 832-843 as shown earlier):

```javascript
  document.getElementById("verkoopdata-kaart").hidden = false;
  document.getElementById("verkoopdata-form").hidden = !kanBeheren;
  try {
    await toonVerkoopdataVoorSelectie();
  } catch (e) {
    toonFout("fout", e.message);
  }
  if (kanBeheren) initVerkoopdataForm();
```

Replace the product-verkoopdata block (currently lines 845-859):

```javascript
  document.getElementById("product-verkoopdata-kaart").hidden = false;
  document.getElementById("product-verkoopdata-form").hidden = !kanBeheren;
  pasProductVerkoopdataPremiumStatusToe(me.in_proefperiode);
  if (!me.in_proefperiode) {
    try {
      await toonProductAdviesVoorSelectie();
    } catch (e) {
      toonFout("fout", e.message);
    }
  }
  if (kanBeheren) initProductVerkoopdataForm();
```

Since `alleEigenWinkels`/the selects are only populated inside the `if (kanBeheren)` branch (Task 12's `verversEigenWinkelsKaart()` call), and `toonVerkoopdataVoorSelectie()`/`toonProductAdviesVoorSelectie()` run for every user including a `lid`, move Task 12's `verversEigenWinkelsKaart()` call (or at minimum a plain `vulEigenWinkelSelects(await haalEigenWinkels())` for a non-eigenaar who can't manage winkels but should still see them in the dropdown) so it always runs before these two new blocks, not only when `kanBeheren`. Concretely: keep the `eigen-winkels-kaart` visibility (`document.getElementById("eigen-winkels-kaart").hidden = false`) and the create-form wiring inside `if (kanBeheren)` as Task 12 left it, but hoist the `haalEigenWinkels()`-and-populate-selects call to run unconditionally, right before the verkoopdata block above:

```javascript
  try {
    alleEigenWinkels = await haalEigenWinkels();
    vulEigenWinkelSelects(alleEigenWinkels);
  } catch (e) {
    toonFout("fout", e.message);
  }
```

Place this new unconditional block immediately before the (now-conditional, `kanBeheren`-only) `eigen-winkels-kaart`/`verversEigenWinkelsKaart()` block from Task 12 — and change that Task-12 block to call `verversEigenWinkelsKaart()` as before (it re-fetches redundantly for an eigenaar, which is fine and keeps that function self-contained for its other callers like the create/rename/delete handlers).

- [ ] **Step 5: Manual verification (no automated test — dashboard JS has none in this codebase)**

Deferred to Task 15.

- [ ] **Step 6: Commit**

```bash
git add dashboard/team.html dashboard/account.js
git commit -m "forecasting: winkel-keuze op verkoopdata- en product-verkoopdata-uploadkaarten"
```

---

### Task 14: `dashboard/account.js` — grafiek duidelijker (labels, gridline, hover-tooltip)

**Files:**
- Modify: `dashboard/account.js` (`tekenVerkoopdataGrafiek`, currently lines 454-490)

No automated test — same existing posture. Verified live in Task 15.

- [ ] **Step 1: Rewrite `tekenVerkoopdataGrafiek()`**

Replace the full function body:

```javascript
function tekenVerkoopdataGrafiek(rijen) {
  const svg = document.getElementById("verkoopdata-grafiek");
  svg.replaceChildren();
  if (rijen.length < 2) return;

  const breedte = 920, hoogte = 200, marge = { boven: 16, rechts: 16, onder: 24, links: 70 };
  const plotBreedte = breedte - marge.links - marge.rechts;
  const plotHoogte = hoogte - marge.boven - marge.onder;
  const omzetten = rijen.map((r) => r.omzet);
  const minY = Math.min(...omzetten) * 0.95;
  const maxY = Math.max(...omzetten) * 1.05 || 1;

  const x = (i) => marge.links + (i / (rijen.length - 1)) * plotBreedte;
  const y = (waarde) => marge.boven + plotHoogte - ((waarde - minY) / (maxY - minY || 1)) * plotHoogte;
  const midY = (minY + maxY) / 2;

  svg.appendChild(maakSvgEl("line", {
    class: "as-gridline", x1: marge.links, x2: breedte - marge.rechts, y1: y(midY), y2: y(midY),
  }));

  svg.appendChild(maakSvgEl("polyline", {
    class: "lijn",
    points: rijen.map((r, i) => `${x(i)},${y(r.omzet)}`).join(" "),
  }));

  for (const waarde of [minY, midY, maxY]) {
    const label = maakSvgEl("text", {
      class: "as-label", x: marge.links - 10, y: y(waarde) + 4, "text-anchor": "end",
    });
    label.textContent = euro.format(Math.round(waarde));
    svg.appendChild(label);
  }

  // Om en nabij elke 5e datapunt een x-as-label, altijd inclusief het
  // eerste en laatste punt, gelijk verdeeld i.p.v. alleen begin/eind.
  const aantalLabels = Math.min(rijen.length, Math.max(2, Math.round(rijen.length / 5) + 1));
  const stap = (rijen.length - 1) / (aantalLabels - 1);
  for (let k = 0; k < aantalLabels; k++) {
    const i = Math.round(k * stap);
    const label = maakSvgEl("text", {
      class: "as-label", x: x(i), y: hoogte - 4,
      "text-anchor": i === 0 ? "start" : i === rijen.length - 1 ? "end" : "middle",
    });
    label.textContent = rijen[i].datum;
    svg.appendChild(label);
  }

  // Hover-hit-target per punt: een onzichtbaar breed staafje (niet enkel
  // een kleine cirkel op het punt zelf) zodat de tooltip ook tussen twee
  // datapunten in makkelijk te raken is, met een native <title> voor de
  // exacte datum + het bedrag — zelfde lichte, library-vrije aanpak als
  // de rest van dit dashboard.
  const hitBreedte = plotBreedte / (rijen.length - 1) || plotBreedte;
  rijen.forEach((r, i) => {
    const staaf = maakSvgEl("rect", {
      class: "hover-hit", x: x(i) - hitBreedte / 2, y: marge.boven, width: hitBreedte, height: plotHoogte,
      fill: "transparent",
    });
    const titel = maakSvgEl("title", {});
    titel.textContent = `${r.datum}: ${euro.format(Math.round(r.omzet))}`;
    staaf.appendChild(titel);
    svg.appendChild(staaf);
  });
}
```

- [ ] **Step 2: Add the gridline/hover-hit CSS classes**

Add to `dashboard/styles.css`, near the existing `.as-label`/`.lijn` SVG-related rules (grep the file for `.as-label` first to place these next to it):

```css
.as-gridline { stroke: var(--rand, #ddd); stroke-width: 1; stroke-dasharray: 2 3; }
.hover-hit { cursor: default; }
```

(Use whatever the existing border/gridline design-token variable name actually is in this file — grep `styles.css` for `--rand` or similar border-color custom property used elsewhere and reuse it rather than introducing a new one; if none exists, use a literal color consistent with the existing light/dark theme blocks, following the same `@media (prefers-color-scheme: dark)` / `:root[data-theme]` pattern already in the file per the Global Constraints of the original spec's Fase-2 dashboard work.)

- [ ] **Step 3: Manual verification (no automated test)**

Deferred to Task 15.

- [ ] **Step 4: Commit**

```bash
git add dashboard/account.js dashboard/styles.css
git commit -m "forecasting: duidelijkere verkoopdata-grafiek (meer datumlabels, gridline, hover-tooltip)"
```

---

### Task 15: Deploy naar kwantiq.tessar.nl en live end-to-end verifiëren

**Files:** none (operational task)

**Interfaces:** none — this task exercises everything built in Tasks 1-14 against the real production server.

- [ ] **Step 1: Run the full local test suite one more time**

Run: `pytest -q` from `forecasting/` with the `DYLD_LIBRARY_PATH`/`PYTHONPATH` prefix from Global Constraints.
Expected: all tests pass except the known-unrelated local xgboost/libomp collection errors (if those resurface, confirm via `git stash` + rerun that they pre-date this branch's changes, don't attempt to fix them here).

- [ ] **Step 2: Drop the two restructured tables on the production server**

Per the spec's migration section — `eigen_verkoopdata`/`eigen_product_verkoopdata` on prod currently only hold the test upload from this session (organisatie "Tessar demo", 30 rows), no real customer data. From the local machine:

```bash
ssh job@157.90.244.24 "cd /home/job/forecasting-demo/deploy && docker compose exec -T api python3 -c \"
from sqlalchemy import create_engine, text
e = create_engine('sqlite:////app/tenants.db')
with e.begin() as c:
    c.execute(text('DROP TABLE IF EXISTS eigen_verkoopdata'))
    c.execute(text('DROP TABLE IF EXISTS eigen_product_verkoopdata'))
print('dropped')
\""
```

Expected output: `dropped`.

- [ ] **Step 3: Sync, rebuild, restart**

```bash
cd /Users/hamdeco/development/hamdoun
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
  --exclude 'data' --exclude 'models' --exclude 'api_keys.json' \
  --exclude 'audit.log' --exclude '.env' --exclude 'tenants.db*' \
  forecasting/ job@157.90.244.24:/home/job/forecasting-demo/
ssh job@157.90.244.24 "cd /home/job/forecasting-demo/deploy && docker compose build"
ssh job@157.90.244.24 "cd /home/job/forecasting-demo/deploy && docker compose up -d && sleep 6 && curl -s http://127.0.0.1:8010/health"
```

Expected: `docker compose build` completes with no errors; `/health` returns `{"status":"ok","model_versie":"20260726T123220Z"}` (same model version as before — this deploy changes no model).

- [ ] **Step 4: Check the server logs for a clean startup**

```bash
ssh job@157.90.244.24 "docker compose -f /home/job/forecasting-demo/deploy/docker-compose.yml logs --tail 30 api"
```

Expected: `Application startup complete.`, no `XGBoostError`/`OperationalError`/`IntegrityError` — the dropped tables should have been silently recreated by `maak_database()`'s `create_all()` at import time (Task 1's schema).

- [ ] **Step 5: Live browser verification**

Using the browser automation tools (same session/cookie already active from earlier in this engagement, or log in fresh as `info@tessar.nl` if the session expired):

1. Navigate to `https://kwantiq.tessar.nl/team.html`.
2. Confirm the "Eigen winkels" card renders with an empty state ("Nog geen eigen winkel...").
3. Create two eigen winkels: "Webshop A" and "Marktkraam".
4. Confirm both appear in the list, and both dropdowns on the two upload cards now show both names.
5. Upload `/Users/hamdeco/Downloads/voorraadlijst-omzet-per-dag.csv` (from earlier in this engagement) against "Webshop A" via the `<select>` + file input — confirm the chart renders with visible intermediate x-axis date labels (not just start/end), a horizontal gridline, and hovering over a point shows a native tooltip with the exact date + amount.
6. Switch the dropdown to "Marktkraam" — confirm the chart/advice area clears (no data yet for this winkel), proving the two winkels are independently scoped.
7. Set a manual price on "Webshop A" via its row's price field + "Opslaan" — confirm it saves and the herbestel-advies below the chart switches from an omzet-based sentence to a stuks-based one.
8. Rename "Marktkraam" to "Markt" — confirm the list and both dropdowns update.
9. Delete "Marktkraam"/"Markt" — confirm it disappears from the list and both dropdowns, with a confirm-dialog shown first.
10. Reload the page fully — confirm "Webshop A" and its data/price persist (proves the server-side state, not just in-memory JS state).
11. Check the browser console for JS errors throughout (`read_console_messages`, `onlyErrors: true`).

- [ ] **Step 6: Report results to the user**

No commit in this step — this is verification only. If any live check in Step 5 fails, stop and fix the underlying task (don't patch around it in this deploy task) before re-running Steps 3-5.
