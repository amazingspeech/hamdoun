# Self-serve pricing model (per-teamlid, per-vestiging, KVK-hergebruik) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move self-serve signup from one flat Stripe price to base (€29/mo) + €5/mo per team member beyond the eigenaar + €10/mo per vestiging beyond the first (declared, billing-only), with a live-updating price on the signup screen, and skip the 14-day free trial for any signup whose KVK-nummer already has an organisation on file.

**Architecture:** `SignupVerzoek` gains `kvk_nummer`/`aantal_leden`/`aantal_winkels`, which flow through the existing pending-signup mechanism (`db.aanmeldingen`) to the Stripe webhook exactly the way `trial_verloopt_op` already does. Stripe billing uses multiple Checkout line items (base + conditional extras) against two new Stripe Price objects created manually in the Stripe dashboard. A repeat KVK-nummer omits `trial_period_days` from the Stripe request (charges immediately) and sets the new organisation's `trial_verloopt_op` to `NULL` (reusing the existing "never in trial" state manually-onboarded organisations already have). Purchased team-member count is enforced as a hard cap on `POST /gebruikers`; purchased vestiging count is billing-only, never enforced.

**Tech Stack:** FastAPI + SQLAlchemy + SQLite backend (Python), Stripe Python SDK 15.3.1, vanilla-JS dashboard frontend (no build step, no framework).

## Global Constraints

- TDD is mandatory for all backend work: RED (watch the real failure) → GREEN → REFACTOR. No exceptions.
- Frontend has no automated test coverage by established project convention — verify live in-browser instead (claude-in-chrome).
- Local test execution is broken (macOS native dependency resolution for xgboost/shap fails) — run backend tests via the established rsync + remote Docker pattern (see Task 1's exact commands, reused verbatim by every later task).
- This entire pricing model applies **only** to the self-serve Stripe signup path (`POST /signup`). Manually onboarded organisations (`db.bootstrap.bootstrap_organisatie` called directly, outside `/signup`) are unaffected — every new parameter this plan adds to `bootstrap_organisatie` must default to `None`/unenforced.
- `aantal_leden` always means the **total** desired user count including the eigenaar (not "extra" members) — this exact semantic must be reflected in the signup form's field label, not just the code.
- "Vestiging" is billing-only in this phase — nothing enforces or reacts to `ingekochte_winkels` anywhere in the backend. Do not add any winkel-count enforcement.
- A `NULL` purchased-seat count (`ingekochte_leden`) means **no limit** — every organisation that existed before this ships has `NULL` here and must never be blocked by the new seat-cap check.
- No self-serve way to change seat/vestiging counts after signup in this phase — a customer who wants more is told to contact support, not offered any in-product upgrade flow.
- The backend never computes or stores a euro amount — it only ever deals in Stripe Price IDs and quantities. Only the frontend needs the actual €29/€5/€10 figures, purely for the live signup-page preview.
- Base price: **€29/month** (confirmed after market research — see spec; corrects the previously-inconsistent €49 shown on the live signup page today).
- Deploy: backend changes require `scp` the changed files to `job@157.90.244.24:/home/job/forecasting-demo/` then `docker compose build api && docker compose up -d` from `deploy/`. `dashboard/*` files are bind-mounted — a plain `scp` makes them live immediately, no rebuild.

---

## File Structure

**Backend:**
- `db/schema.py` (modify) — `aanmeldingen` gains `kvk_nummer`, `aantal_leden`, `aantal_winkels`, `was_kvk_herhaling`. `organisaties` gains `kvk_nummer`, `ingekochte_leden`, `ingekochte_winkels`. All nullable, via the existing auto-migration path.
- `db/aanmeldingen.py` (modify) — `maak_aanmelding()` accepts the four new fields.
- `db/organisaties.py` (modify) — new `kvk_nummer_heeft_organisatie()`, `haal_ingekochte_leden()`, `haal_ingekochte_winkels()`.
- `db/bootstrap.py` (modify) — `bootstrap_organisatie()` gains optional `kvk_nummer`/`ingekochte_leden`/`ingekochte_winkels` parameters.
- `db/gebruikers.py` (modify) — new `aantal_actieve_gebruikers()`.
- `serving/betaalintegratie.py` (modify) — `maak_checkout_sessie()`: `proefperiode_dagen` becomes optional (omits `trial_period_days` entirely when falsy, rather than sending `0`, which Stripe rejects); new optional `extra_line_items` parameter for the seat/vestiging add-on lines.
- `serving/config.py` (modify) — new `stripe_price_id_extra_lid`, `stripe_price_id_extra_winkel` settings.
- `serving/schemas.py` (modify) — `SignupVerzoek` gains `kvk_nummer`, `aantal_leden`, `aantal_winkels`.
- `serving/app.py` (modify) — `POST /signup` (KVK check, price computation, extended `aanmeldingen` write), `POST /webhooks/stripe` (writes the three new fields onto the new organisation, sets `trial_verloopt_op` per the repeat-KVK rule), `POST /gebruikers` (seat-cap check), `GET /me` (exposes `ingekochte_leden`/`ingekochte_winkels`).

**Frontend:**
- `dashboard/signup.html` + `dashboard/account.js` — new KVK-nummer/teamleden/vestigingen fields, live price preview, corrected base-price and trial-length copy.
- `dashboard/team.html` — read-only purchased-counts display.

**Tests:**
- `tests/test_db_aanmeldingen.py`, a new/extended section for `maak_aanmelding()`'s new fields.
- `tests/test_db_organisaties.py` (or wherever `db.organisaties` is tested — extend or create), for the three new functions.
- `tests/test_db_bootstrap.py`, extended for the new `bootstrap_organisatie()` parameters.
- `tests/test_db_gebruikers.py`, extended for `aantal_actieve_gebruikers()`.
- `tests/test_betaalintegratie.py`, extended for optional trial + extra line items.
- `tests/test_config.py`, extended for the two new settings.
- `tests/test_signup_endpoint.py`, extended for KVK/leden/winkels behavior.
- `tests/test_stripe_webhook_endpoint.py`, extended for the new organisation fields and repeat-KVK trial-skip.
- `tests/test_gebruikers_endpoint.py`, extended for the seat cap.

---

### Task 1: `db/aanmeldingen.py` — extend `maak_aanmelding()` with KVK/seat/vestiging fields

**Files:**
- Modify: `db/schema.py` (the `aanmeldingen` table definition)
- Modify: `db/aanmeldingen.py`
- Test: `tests/test_db_aanmeldingen.py` (create if it doesn't already exist as a standalone file — otherwise add to it)

**Interfaces:**
- Produces: `maak_aanmelding(engine, organisatie_naam, organisatie_slug, email, wachtwoord_hash, wachtwoord_salt, stripe_checkout_session_id, kvk_nummer: str, aantal_leden: int, aantal_winkels: int, was_kvk_herhaling: bool) -> int`. The row returned by `haal_aanmelding_bij_sessie()` (unchanged function) will now also carry `.kvk_nummer`, `.aantal_leden`, `.aantal_winkels`, `.was_kvk_herhaling` as plain attribute access (SQLAlchemy `Row` behavior — no code change needed there, but later tasks rely on these being present).

- [ ] **Step 1: Write the failing test**

Create (or add to) `tests/test_db_aanmeldingen.py`:

```python
from db.aanmeldingen import haal_aanmelding_bij_sessie, maak_aanmelding
from db.schema import maak_database


def test_maak_aanmelding_slaat_kvk_en_aantallen_op(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")

    maak_aanmelding(
        engine, organisatie_naam="Bakkerij De Vries", organisatie_slug="bakkerij-de-vries",
        email="devries@voorbeeld.nl", wachtwoord_hash="hash", wachtwoord_salt="salt",
        stripe_checkout_session_id="cs_test_123",
        kvk_nummer="12345678", aantal_leden=3, aantal_winkels=2, was_kvk_herhaling=False,
    )

    rij = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    assert rij.kvk_nummer == "12345678"
    assert rij.aantal_leden == 3
    assert rij.aantal_winkels == 2
    assert rij.was_kvk_herhaling is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_aanmeldingen.py -v -k kvk_en_aantallen'"
```

Expected: FAIL with `TypeError: maak_aanmelding() got an unexpected keyword argument 'kvk_nummer'`.

- [ ] **Step 3: Add the columns to `db/schema.py`**

In the `aanmeldingen` table definition, right after the existing `Column("stripe_checkout_session_id", String, nullable=False, unique=True),` line, add:

```python
    # Fase 6 prijsmodel: KVK-nummer en gewenste aantallen, vastgelegd bij
    # /signup en overgenomen op de organisatie zodra de webhook de
    # aanmelding voltooit (zie serving/app.py). was_kvk_herhaling wordt bij
    # /signup bepaald en hier bewaard (niet opnieuw afgeleid in de webhook),
    # zodat een gelijktijdige tweede aanmelding onder hetzelfde, nieuwe
    # KVK-nummer niet per ongeluk allebei als "eerste" tellen.
    Column("kvk_nummer", String, nullable=True),
    Column("aantal_leden", Integer, nullable=True),
    Column("aantal_winkels", Integer, nullable=True),
    Column("was_kvk_herhaling", Boolean, nullable=True),
```

(`Integer`, `String`, `Boolean` are already imported at the top of `db/schema.py` — used by other tables in the same file.)

- [ ] **Step 4: Implement in `db/aanmeldingen.py`**

Change `maak_aanmelding()`:

```python
def maak_aanmelding(
    engine: Engine,
    organisatie_naam: str,
    organisatie_slug: str,
    email: str,
    wachtwoord_hash: str,
    wachtwoord_salt: str,
    stripe_checkout_session_id: str,
    kvk_nummer: str,
    aantal_leden: int,
    aantal_winkels: int,
    was_kvk_herhaling: bool,
) -> int:
    with engine.begin() as conn:
        return conn.execute(
            aanmeldingen.insert().values(
                organisatie_naam=organisatie_naam,
                organisatie_slug=organisatie_slug,
                email=email,
                wachtwoord_hash=wachtwoord_hash,
                wachtwoord_salt=wachtwoord_salt,
                stripe_checkout_session_id=stripe_checkout_session_id,
                kvk_nummer=kvk_nummer,
                aantal_leden=aantal_leden,
                aantal_winkels=aantal_winkels,
                was_kvk_herhaling=was_kvk_herhaling,
                organisatie_id=None,
                voltooid_op=None,
                aangemaakt_op=datetime.now(timezone.utc),
            )
        ).inserted_primary_key[0]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_aanmeldingen.py -v'"
```

Expected: PASS. (This will also break `tests/test_signup_endpoint.py` and `tests/test_stripe_webhook_endpoint.py`, which call `maak_aanmelding` without the new required arguments — that's expected and fixed in Tasks 7 and 8 respectively. Do not fix those files in this task.)

- [ ] **Step 6: Commit**

```bash
git add db/schema.py db/aanmeldingen.py tests/test_db_aanmeldingen.py
git commit -m "feat: store KVK-nummer and desired seat/vestiging counts on aanmeldingen"
```

---

### Task 2: `db/organisaties.py` — KVK lookup + purchased-count getters

**Files:**
- Modify: `db/schema.py` (the `organisaties` table definition)
- Modify: `db/organisaties.py`
- Test: `tests/test_db_organisaties.py` (create if it doesn't already exist as a standalone file — otherwise add to it)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `kvk_nummer_heeft_organisatie(engine, kvk_nummer: str) -> bool`, `haal_ingekochte_leden(engine, organisatie_id: int) -> Optional[int]`, `haal_ingekochte_winkels(engine, organisatie_id: int) -> Optional[int]`. Later tasks (3, 8, 9) rely on these exact names and signatures.

- [ ] **Step 1: Write the failing tests**

Create (or add to) `tests/test_db_organisaties.py`:

```python
from db.bootstrap import bootstrap_organisatie
from db.organisaties import haal_ingekochte_leden, haal_ingekochte_winkels, kvk_nummer_heeft_organisatie
from db.schema import maak_database


def test_kvk_nummer_heeft_organisatie_onbekend_geeft_false(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    assert kvk_nummer_heeft_organisatie(engine, "12345678") is False


def test_kvk_nummer_heeft_organisatie_bekend_geeft_true(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[], kvk_nummer="12345678")
    assert kvk_nummer_heeft_organisatie(engine, "12345678") is True


def test_haal_ingekochte_leden_zonder_waarde_geeft_none(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Handmatige Klant", slug="handmatige-klant", store_ids=[])
    assert haal_ingekochte_leden(engine, org_id) is None


def test_haal_ingekochte_leden_met_waarde(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[], ingekochte_leden=3)
    assert haal_ingekochte_leden(engine, org_id) == 3


def test_haal_ingekochte_winkels_met_waarde(tmp_path):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[], ingekochte_winkels=2)
    assert haal_ingekochte_winkels(engine, org_id) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_organisaties.py -v'"
```

(Re-run the `rsync` from Task 1 Step 2 first if you're in a fresh session.) Expected: all FAIL — `kvk_nummer_heeft_organisatie` etc. don't exist yet, and `bootstrap_organisatie` doesn't accept `kvk_nummer`/`ingekochte_leden`/`ingekochte_winkels` yet (that part is fixed in Task 3, but these tests need it — see the note at the end of this task).

- [ ] **Step 3: Add the columns to `db/schema.py`**

In the `organisaties` table definition, right after the existing `Column("trial_verloopt_op", DateTime, nullable=True),` line, add:

```python
    # Fase 6 prijsmodel: alleen gevuld voor self-serve organisaties (via
    # /signup) — handmatig aangemaakte organisaties (db/bootstrap.py) hebben
    # deze niet. ingekochte_leden/ingekochte_winkels: NULL betekent "geen
    # limiet" — zowel voor elke organisatie van vóór dit prijsmodel als voor
    # elke handmatig aangemaakte organisatie. Zie db.organisaties.
    # haal_ingekochte_leden() en de aanroep in POST /gebruikers.
    Column("kvk_nummer", String, nullable=True),
    Column("ingekochte_leden", Integer, nullable=True),
    Column("ingekochte_winkels", Integer, nullable=True),
```

- [ ] **Step 4: Implement the three functions in `db/organisaties.py`**

Add to the end of the file:

```python
def kvk_nummer_heeft_organisatie(engine: Engine, kvk_nummer: str) -> bool:
    with engine.connect() as conn:
        rij = conn.execute(select(organisaties.c.id).where(organisaties.c.kvk_nummer == kvk_nummer)).first()
    return rij is not None


def haal_ingekochte_leden(engine: Engine, organisatie_id: int) -> Optional[int]:
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.ingekochte_leden).where(organisaties.c.id == organisatie_id)
        ).scalar_one_or_none()


def haal_ingekochte_winkels(engine: Engine, organisatie_id: int) -> Optional[int]:
    with engine.connect() as conn:
        return conn.execute(
            select(organisaties.c.ingekochte_winkels).where(organisaties.c.id == organisatie_id)
        ).scalar_one_or_none()
```

Note: these tests won't fully pass until Task 3 (below) extends `bootstrap_organisatie` to accept `kvk_nummer`/`ingekochte_leden`/`ingekochte_winkels`. Do Task 3 immediately after this step, before running Step 5.

- [ ] **Step 5: Run tests to verify they pass (after also completing Task 3)**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_organisaties.py -v'"
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add db/schema.py db/organisaties.py tests/test_db_organisaties.py
git commit -m "feat: add KVK lookup and purchased-seat/vestiging getters to db.organisaties"
```

---

### Task 3: `db/bootstrap.py` — extend `bootstrap_organisatie()` with KVK/seat/vestiging

**Files:**
- Modify: `db/bootstrap.py`
- Test: `tests/test_db_bootstrap.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `bootstrap_organisatie(engine, naam, slug, store_ids, conn=None, trial_verloopt_op=None, kvk_nummer: Optional[str] = None, ingekochte_leden: Optional[int] = None, ingekochte_winkels: Optional[int] = None) -> int`. Task 2's tests and Task 8's webhook changes rely on these exact parameter names.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_db_bootstrap.py`:

```python
def test_bootstrap_organisatie_slaat_kvk_en_aantallen_op(tmp_path):
    from sqlalchemy import select

    from db.schema import maak_database, organisaties

    engine = maak_database(tmp_path / "tenants.db")

    org_id = bootstrap_organisatie(
        engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[],
        kvk_nummer="12345678", ingekochte_leden=3, ingekochte_winkels=2,
    )

    with engine.connect() as conn:
        org = conn.execute(select(organisaties).where(organisaties.c.id == org_id)).one()
    assert org.kvk_nummer == "12345678"
    assert org.ingekochte_leden == 3
    assert org.ingekochte_winkels == 2


def test_bootstrap_organisatie_zonder_kvk_en_aantallen_geeft_none(tmp_path):
    from sqlalchemy import select

    from db.schema import maak_database, organisaties

    engine = maak_database(tmp_path / "tenants.db")

    org_id = bootstrap_organisatie(engine, naam="Handmatige Klant", slug="handmatige-klant", store_ids=[])

    with engine.connect() as conn:
        org = conn.execute(select(organisaties).where(organisaties.c.id == org_id)).one()
    assert org.kvk_nummer is None
    assert org.ingekochte_leden is None
    assert org.ingekochte_winkels is None
```

(If `tests/test_db_bootstrap.py` doesn't already import `bootstrap_organisatie` at module level, add `from db.bootstrap import bootstrap_organisatie` at the top.)

- [ ] **Step 2: Run tests to verify they fail**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_bootstrap.py -v -k kvk_en_aantallen'"
```

Expected: FAIL with `TypeError: bootstrap_organisatie() got an unexpected keyword argument 'kvk_nummer'`.

- [ ] **Step 3: Implement**

In `db/bootstrap.py`, change both `_bootstrap_organisatie_op_connectie` and the public `bootstrap_organisatie`:

```python
def _bootstrap_organisatie_op_connectie(
    conn: Connection, naam: str, slug: str, store_ids: list[int], trial_verloopt_op: Optional[datetime] = None,
    kvk_nummer: Optional[str] = None, ingekochte_leden: Optional[int] = None,
    ingekochte_winkels: Optional[int] = None,
) -> int:
    nu = datetime.now(timezone.utc)
    org_id = conn.execute(
        organisaties.insert().values(
            naam=naam, slug=slug, actief=True, aangemaakt_op=nu, trial_verloopt_op=trial_verloopt_op,
            kvk_nummer=kvk_nummer, ingekochte_leden=ingekochte_leden, ingekochte_winkels=ingekochte_winkels,
        )
    ).inserted_primary_key[0]

    if store_ids:
        conn.execute(
            winkels.insert(),
            [
                {
                    "organisatie_id": org_id,
                    "extern_store_id": store_id,
                    "naam": None,
                    "actief": True,
                    "aangemaakt_op": nu,
                }
                for store_id in store_ids
            ],
        )
    return org_id


def bootstrap_organisatie(
    engine: Engine, naam: str, slug: str, store_ids: list[int], conn: Optional[Connection] = None,
    trial_verloopt_op: Optional[datetime] = None, kvk_nummer: Optional[str] = None,
    ingekochte_leden: Optional[int] = None, ingekochte_winkels: Optional[int] = None,
) -> int:
    """Maakt één organisatie aan en koppelt elke store_id uit store_ids
    eraan als winkel. Geeft het id van de aangemaakte organisatie terug.
    Faalt hard (IntegrityError) bij een dubbele slug of een store_id die al
    aan een andere organisatie hangt — nooit stilzwijgend overschrijven.

    conn: optioneel een al-openstaande connectie/transactie (bv. vanuit
    serving.app's Stripe-webhook, die dit met andere schrijfacties atomisch
    moet combineren — zie db/organisaties.py en db/aanmeldingen.py voor
    hetzelfde patroon). Zonder conn opent deze functie zoals voorheen zijn
    eigen transactie.

    trial_verloopt_op: optioneel, alleen door de Stripe-webhook meegegeven
    zodat de lokale proefperiode-status (db.organisaties.is_in_proefperiode)
    Stripe's eigen trial_period_days volgt. Standaard None — een handmatige
    bootstrap (db/cli.py) is per ontwerp nooit trial-beperkt.

    kvk_nummer/ingekochte_leden/ingekochte_winkels: optioneel, alleen door
    de Stripe-webhook meegegeven voor self-serve organisaties (Fase 6
    prijsmodel) — een handmatige bootstrap heeft hier per ontwerp nooit
    waarden voor (geen KVK-check, geen zetel-limiet)."""
    if conn is not None:
        return _bootstrap_organisatie_op_connectie(
            conn, naam, slug, store_ids, trial_verloopt_op, kvk_nummer, ingekochte_leden, ingekochte_winkels
        )
    with engine.begin() as eigen_conn:
        return _bootstrap_organisatie_op_connectie(
            eigen_conn, naam, slug, store_ids, trial_verloopt_op, kvk_nummer, ingekochte_leden, ingekochte_winkels
        )
```

- [ ] **Step 4: Run tests to verify they pass (this also unblocks Task 2's tests)**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_bootstrap.py tests/test_db_organisaties.py -v'"
```

Expected: PASS (both files).

- [ ] **Step 5: Commit**

```bash
git add db/bootstrap.py tests/test_db_bootstrap.py
git commit -m "feat: let bootstrap_organisatie accept KVK-nummer and purchased seat/vestiging counts"
```

---

### Task 4: `db/gebruikers.py` — active-member count

**Files:**
- Modify: `db/gebruikers.py`
- Test: `tests/test_db_gebruikers.py`

**Interfaces:**
- Produces: `aantal_actieve_gebruikers(engine, organisatie_id: int) -> int`. Task 9's seat-cap check relies on this exact name.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_db_gebruikers.py`:

```python
def test_aantal_actieve_gebruikers(tmp_path):
    from db.bootstrap import bootstrap_organisatie
    from db.gebruikers import aantal_actieve_gebruikers, maak_gebruiker
    from db.schema import maak_database

    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@voorbeeld.nl", wachtwoord="wachtwoord-1", rol="eigenaar")
    maak_gebruiker(engine, organisatie_id=org_id, email="lid@voorbeeld.nl", wachtwoord="wachtwoord-2", rol="lid")

    assert aantal_actieve_gebruikers(engine, org_id) == 2


def test_aantal_actieve_gebruikers_negeert_andere_organisatie(tmp_path):
    from db.bootstrap import bootstrap_organisatie
    from db.gebruikers import aantal_actieve_gebruikers, maak_gebruiker
    from db.schema import maak_database

    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Organisatie B", slug="org-b", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_a, email="eigenaar-a@voorbeeld.nl", wachtwoord="wachtwoord-1", rol="eigenaar")
    maak_gebruiker(engine, organisatie_id=org_b, email="eigenaar-b@voorbeeld.nl", wachtwoord="wachtwoord-2", rol="eigenaar")

    assert aantal_actieve_gebruikers(engine, org_a) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_gebruikers.py -v -k aantal_actieve_gebruikers'"
```

Expected: FAIL with `ImportError: cannot import name 'aantal_actieve_gebruikers'`.

- [ ] **Step 3: Implement**

In `db/gebruikers.py`, change the import line `from sqlalchemy import select` to `from sqlalchemy import func, select`, then add this function anywhere after the imports (e.g. right after `maak_gebruiker`):

```python
def aantal_actieve_gebruikers(engine: Engine, organisatie_id: int) -> int:
    with engine.connect() as conn:
        return conn.execute(
            select(func.count()).select_from(gebruikers).where(
                gebruikers.c.organisatie_id == organisatie_id, gebruikers.c.actief.is_(True)
            )
        ).scalar_one()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_db_gebruikers.py -v'"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add db/gebruikers.py tests/test_db_gebruikers.py
git commit -m "feat: add aantal_actieve_gebruikers for the upcoming seat-cap check"
```

---

### Task 5: `serving/betaalintegratie.py` — optional trial + extra line items

**Files:**
- Modify: `serving/betaalintegratie.py`
- Test: `tests/test_betaalintegratie.py`

**Interfaces:**
- Produces: `maak_checkout_sessie(stripe_secret_key, price_id, klant_email, success_url, cancel_url, metadata, proefperiode_dagen: Optional[int], extra_line_items: Optional[list[dict]] = None) -> CheckoutSessie`. Task 7's `/signup` rewrite relies on this exact signature.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_betaalintegratie.py`:

```python
def test_maak_checkout_sessie_zonder_proefperiode_stuurt_geen_trial_period_days(monkeypatch):
    aangeroepen_met = {}

    def _nep_create(**kwargs):
        aangeroepen_met.update(kwargs)
        return _NepSessie(id="cs_test_123", url="https://checkout.stripe.com/c/pay/cs_test_123")

    monkeypatch.setattr(betaalintegratie.stripe.checkout.Session, "create", _nep_create)

    betaalintegratie.maak_checkout_sessie(
        stripe_secret_key="sk_test_geheim",
        price_id="price_abc",
        klant_email="devries@voorbeeld.nl",
        success_url="https://app.voorbeeld.nl/signup-gelukt.html",
        cancel_url="https://app.voorbeeld.nl/signup.html",
        metadata={"aanmelding_id": "42"},
        proefperiode_dagen=None,
    )

    assert aangeroepen_met["subscription_data"] == {}


def test_maak_checkout_sessie_met_extra_line_items(monkeypatch):
    aangeroepen_met = {}

    def _nep_create(**kwargs):
        aangeroepen_met.update(kwargs)
        return _NepSessie(id="cs_test_123", url="https://checkout.stripe.com/c/pay/cs_test_123")

    monkeypatch.setattr(betaalintegratie.stripe.checkout.Session, "create", _nep_create)

    betaalintegratie.maak_checkout_sessie(
        stripe_secret_key="sk_test_geheim",
        price_id="price_abc",
        klant_email="devries@voorbeeld.nl",
        success_url="https://app.voorbeeld.nl/signup-gelukt.html",
        cancel_url="https://app.voorbeeld.nl/signup.html",
        metadata={"aanmelding_id": "42"},
        proefperiode_dagen=14,
        extra_line_items=[{"price": "price_extra_lid", "quantity": 2}, {"price": "price_extra_winkel", "quantity": 1}],
    )

    assert aangeroepen_met["line_items"] == [
        {"price": "price_abc", "quantity": 1},
        {"price": "price_extra_lid", "quantity": 2},
        {"price": "price_extra_winkel", "quantity": 1},
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_betaalintegratie.py -v'"
```

Expected: the two new tests FAIL — `test_maak_checkout_sessie_zonder_proefperiode_stuurt_geen_trial_period_days` fails because `subscription_data` is currently always `{"trial_period_days": None}`, not `{}`; `test_maak_checkout_sessie_met_extra_line_items` fails with `TypeError: maak_checkout_sessie() got an unexpected keyword argument 'extra_line_items'`. The existing `test_maak_checkout_sessie_geeft_id_en_url_terug` (which passes `proefperiode_dagen=7`) should still PASS unmodified — confirm it does.

- [ ] **Step 3: Implement**

In `serving/betaalintegratie.py`, add `Optional` to the imports (`from typing import NamedTuple, Optional`) and change `maak_checkout_sessie`:

```python
def maak_checkout_sessie(
    stripe_secret_key: str,
    price_id: str,
    klant_email: str,
    success_url: str,
    cancel_url: str,
    metadata: dict,
    proefperiode_dagen: Optional[int],
    extra_line_items: Optional[list[dict]] = None,
) -> CheckoutSessie:
    line_items = [{"price": price_id, "quantity": 1}]
    if extra_line_items:
        line_items.extend(extra_line_items)
    # Stripe accepteert geen trial_period_days van 0 (moet een positief
    # getal zijn als het veld aanwezig is) — voor "geen proefperiode" laat
    # dit het veld helemaal weg i.p.v. een 0 te sturen die Stripe zou
    # afwijzen.
    subscription_data = {"trial_period_days": proefperiode_dagen} if proefperiode_dagen else {}
    sessie = stripe.checkout.Session.create(
        api_key=stripe_secret_key,
        mode="subscription",
        line_items=line_items,
        customer_email=klant_email,
        success_url=success_url,
        cancel_url=cancel_url,
        subscription_data=subscription_data,
        metadata=metadata,
    )
    return CheckoutSessie(id=sessie.id, checkout_url=sessie.url)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_betaalintegratie.py -v'"
```

Expected: all PASS, including the pre-existing test.

- [ ] **Step 5: Commit**

```bash
git add serving/betaalintegratie.py tests/test_betaalintegratie.py
git commit -m "feat: support omitting the trial period and adding extra Stripe line items"
```

---

### Task 6: `serving/config.py` — two new Stripe price-ID settings

**Files:**
- Modify: `serving/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Settings.stripe_price_id_extra_lid: Optional[str]`, `Settings.stripe_price_id_extra_winkel: Optional[str]`, read from `STRIPE_PRICE_ID_EXTRA_LID`/`STRIPE_PRICE_ID_EXTRA_WINKEL`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py`:

```python
def test_laad_settings_zonder_extra_prijzen_geeft_none(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path)
    for var in ("STRIPE_PRICE_ID_EXTRA_LID", "STRIPE_PRICE_ID_EXTRA_WINKEL"):
        monkeypatch.delenv(var, raising=False)
    settings = config.laad_settings()
    assert settings.stripe_price_id_extra_lid is None
    assert settings.stripe_price_id_extra_winkel is None


def test_laad_settings_leest_extra_prijzen(monkeypatch, tmp_path):
    _basis_env(
        monkeypatch, tmp_path,
        STRIPE_PRICE_ID_EXTRA_LID="price_extra_lid", STRIPE_PRICE_ID_EXTRA_WINKEL="price_extra_winkel",
    )
    settings = config.laad_settings()
    assert settings.stripe_price_id_extra_lid == "price_extra_lid"
    assert settings.stripe_price_id_extra_winkel == "price_extra_winkel"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_config.py -v -k extra_prijzen'"
```

Expected: both FAIL with `AttributeError: 'Settings' object has no attribute 'stripe_price_id_extra_lid'`.

- [ ] **Step 3: Implement**

In `serving/config.py`, add to the `Settings` dataclass right after `stripe_price_id: Optional[str] = None`:

```python
    stripe_price_id_extra_lid: Optional[str] = None
    stripe_price_id_extra_winkel: Optional[str] = None
```

In `laad_settings()`, add the two fields to the returned `Settings(...)` call, right after `stripe_price_id=os.environ.get("STRIPE_PRICE_ID"),`:

```python
        stripe_price_id_extra_lid=os.environ.get("STRIPE_PRICE_ID_EXTRA_LID"),
        stripe_price_id_extra_winkel=os.environ.get("STRIPE_PRICE_ID_EXTRA_WINKEL"),
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_config.py -v'"
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add serving/config.py tests/test_config.py
git commit -m "feat: add settings for the extra-teamlid and extra-vestiging Stripe prices"
```

---

### Task 7: `POST /signup` — KVK-nummer, seat/vestiging fields, price computation

**Files:**
- Modify: `serving/schemas.py`
- Modify: `serving/app.py`
- Test: `tests/test_signup_endpoint.py`

**Interfaces:**
- Consumes: `maak_checkout_sessie(..., extra_line_items=...)` (Task 5), `Settings.stripe_price_id_extra_lid`/`stripe_price_id_extra_winkel` (Task 6), `db_organisaties.kvk_nummer_heeft_organisatie` (Task 2), `db_aanmeldingen.maak_aanmelding(..., kvk_nummer, aantal_leden, aantal_winkels, was_kvk_herhaling)` (Task 1).
- Produces: `SignupVerzoek` now requires `kvk_nummer` (8 digits) and accepts optional `aantal_leden`/`aantal_winkels` (default 1 each).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_signup_endpoint.py`. First, extend `_bouw_omgeving`'s `met_stripe_config` branch to also set the two new env vars:

```python
    if met_stripe_config:
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_geheim")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_geheim")
        monkeypatch.setenv("STRIPE_PRICE_ID", "price_abc")
        monkeypatch.setenv("STRIPE_PRICE_ID_EXTRA_LID", "price_extra_lid")
        monkeypatch.setenv("STRIPE_PRICE_ID_EXTRA_WINKEL", "price_extra_winkel")
        monkeypatch.setenv("APP_BASIS_URL", "http://127.0.0.1:8000")
    else:
        for var in (
            "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_ID",
            "STRIPE_PRICE_ID_EXTRA_LID", "STRIPE_PRICE_ID_EXTRA_WINKEL", "APP_BASIS_URL",
        ):
            monkeypatch.delenv(var, raising=False)
```

Then update the existing `test_signup_geeft_checkout_url_terug` test's request body to include `kvk_nummer` (every existing signup request in this file needs this now — it's a required field):

```python
    resp = client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
        "kvk_nummer": "12345678",
    })
```

Apply this same `"kvk_nummer": "12345678"` addition to every `client.post("/signup", json={...})` call already in this file (`test_signup_legt_aanmelding_vast_met_gehasht_wachtwoord`, `test_signup_met_al_bestaand_email_geeft_409`, `test_signup_zonder_stripeconfig_geeft_503`, `test_signup_te_kort_wachtwoord_geeft_422`) — otherwise those requests will now fail 422 validation before reaching the behavior under test.

Then add the new tests:

```python
def test_signup_zonder_kvk_nummer_geeft_422(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _fake_checkout_sessie(module, monkeypatch)

    resp = client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
    })

    assert resp.status_code == 422


def test_signup_met_ongeldig_kvk_nummer_geeft_422(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _fake_checkout_sessie(module, monkeypatch)

    resp = client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
        "kvk_nummer": "niet-acht-cijfers",
    })

    assert resp.status_code == 422


def test_signup_default_aantallen_geeft_geen_extra_line_items(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    aangeroepen_met = _fake_checkout_sessie(module, monkeypatch)

    client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
        "kvk_nummer": "12345678",
    })

    assert aangeroepen_met["extra_line_items"] is None
    assert aangeroepen_met["proefperiode_dagen"] == 14


def test_signup_met_extra_leden_en_winkels_bouwt_line_items(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    aangeroepen_met = _fake_checkout_sessie(module, monkeypatch)

    client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
        "kvk_nummer": "12345678", "aantal_leden": 3, "aantal_winkels": 2,
    })

    assert aangeroepen_met["extra_line_items"] == [
        {"price": "price_extra_lid", "quantity": 2},
        {"price": "price_extra_winkel", "quantity": 1},
    ]


def test_signup_herhaald_kvk_nummer_slaat_proefperiode_over(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    aangeroepen_met = _fake_checkout_sessie(module, monkeypatch)
    from db.bootstrap import bootstrap_organisatie
    bootstrap_organisatie(engine, naam="Bestaande Vestiging", slug="bestaande-vestiging", store_ids=[], kvk_nummer="12345678")

    client.post("/signup", json={
        "organisatie_naam": "Tweede Vestiging", "email": "tweede@voorbeeld.nl", "wachtwoord": "correct-paard",
        "kvk_nummer": "12345678",
    })

    assert aangeroepen_met["proefperiode_dagen"] is None


def test_signup_slaat_kvk_en_aantallen_op_in_aanmelding(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _fake_checkout_sessie(module, monkeypatch)

    client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
        "kvk_nummer": "12345678", "aantal_leden": 3, "aantal_winkels": 2,
    })

    from db.aanmeldingen import haal_aanmelding_bij_sessie
    rij = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    assert rij.kvk_nummer == "12345678"
    assert rij.aantal_leden == 3
    assert rij.aantal_winkels == 2
    assert rij.was_kvk_herhaling is False


def test_signup_zonder_extra_prijs_configuratie_geeft_503(tmp_path, monkeypatch):
    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    monkeypatch.delenv("STRIPE_PRICE_ID_EXTRA_LID", raising=False)
    import dataclasses
    module.settings = dataclasses.replace(module.settings, stripe_price_id_extra_lid=None)

    resp = client.post("/signup", json={
        "organisatie_naam": "Bakkerij De Vries", "email": "devries@voorbeeld.nl", "wachtwoord": "correct-paard",
        "kvk_nummer": "12345678",
    })

    assert resp.status_code == 503
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_signup_endpoint.py -v'"
```

Expected: the pre-existing tests now FAIL 422 (missing `kvk_nummer` before you add it to their request bodies in Step 1 — make sure you've done that edit), and the new tests FAIL because the schema/endpoint don't support the new fields yet.

- [ ] **Step 3: Extend `SignupVerzoek` in `serving/schemas.py`**

```python
class SignupVerzoek(BaseModel):
    organisatie_naam: str = Field(..., min_length=1)
    email: str
    wachtwoord: str = Field(..., min_length=8)
    # Nederlands KVK-nummer: alleen formaat gecontroleerd (8 cijfers), niet
    # tegen het echte KVK-register geverifieerd — zie de spec voor de
    # afweging. Gebruikt om "hetzelfde bedrijf meldt zich opnieuw aan" te
    # herkennen (dan geen gratis proefperiode).
    kvk_nummer: str = Field(..., pattern=r"^\d{8}$")
    # Totaal gewenst aantal gebruikers, INCLUSIEF de eigenaar (niet "extra"
    # bovenop de eigenaar) — moet exact overeenkomen met wat het
    # aanmeldformulier als label toont.
    aantal_leden: int = Field(default=1, ge=1)
    # Gewenst aantal vestigingen — puur voor prijsberekening in deze fase,
    # geen technische winkel-koppeling (zie spec, "Explicitly out of scope").
    aantal_winkels: int = Field(default=1, ge=1)
```

- [ ] **Step 4: Rewrite `POST /signup` in `serving/app.py`**

Replace the whole function body:

```python
@app.post("/signup", response_model=SignupResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute", key_func=get_remote_address)
def signup(request: Request, verzoek: SignupVerzoek) -> SignupResponse:
    """Publiek, geen sessie nodig — start een Stripe Checkout Session met
    proefperiode. De organisatie + eigenaar-account bestaan hierna nog
    NIET; die ontstaan pas als Stripe de betaling bevestigt via
    POST /webhooks/stripe. Zie db/aanmeldingen.py voor de tussentoestand."""
    if not all([
        settings.stripe_secret_key, settings.stripe_price_id, settings.stripe_price_id_extra_lid,
        settings.stripe_price_id_extra_winkel, settings.app_basis_url,
    ]):
        raise HTTPException(status_code=503, detail="Self-serve aanmelden is nog niet geconfigureerd.")

    if db_gebruikers.email_is_in_gebruik(tenants_db, email=verzoek.email):
        raise HTTPException(status_code=409, detail=f"E-mailadres {verzoek.email} is al in gebruik.")

    wachtwoord_hash, wachtwoord_salt = hash_key(verzoek.wachtwoord)
    slug = db_aanmeldingen.genereer_unieke_organisatie_slug(tenants_db, verzoek.organisatie_naam)

    # Herhaalde KVK-aanmelding wordt bewust NIET geblokkeerd (de eigenaar
    # wil juist meerdere bedrijven onder één KVK aanmoedigen), maar krijgt
    # geen gratis proefperiode meer — zie spec.
    was_kvk_herhaling = db_organisaties.kvk_nummer_heeft_organisatie(tenants_db, verzoek.kvk_nummer)

    extra_line_items = []
    if verzoek.aantal_leden > 1:
        extra_line_items.append(
            {"price": settings.stripe_price_id_extra_lid, "quantity": verzoek.aantal_leden - 1}
        )
    if verzoek.aantal_winkels > 1:
        extra_line_items.append(
            {"price": settings.stripe_price_id_extra_winkel, "quantity": verzoek.aantal_winkels - 1}
        )

    sessie = maak_checkout_sessie(
        stripe_secret_key=settings.stripe_secret_key,
        price_id=settings.stripe_price_id,
        klant_email=verzoek.email,
        success_url=f"{settings.app_basis_url}/signup-gelukt.html",
        cancel_url=f"{settings.app_basis_url}/signup.html",
        metadata={"organisatie_naam": verzoek.organisatie_naam},
        proefperiode_dagen=None if was_kvk_herhaling else SIGNUP_PROEFPERIODE_DAGEN,
        extra_line_items=extra_line_items or None,
    )

    db_aanmeldingen.maak_aanmelding(
        tenants_db,
        organisatie_naam=verzoek.organisatie_naam,
        organisatie_slug=slug,
        email=verzoek.email,
        wachtwoord_hash=wachtwoord_hash,
        wachtwoord_salt=wachtwoord_salt,
        stripe_checkout_session_id=sessie.id,
        kvk_nummer=verzoek.kvk_nummer,
        aantal_leden=verzoek.aantal_leden,
        aantal_winkels=verzoek.aantal_winkels,
        was_kvk_herhaling=was_kvk_herhaling,
    )
    return SignupResponse(checkout_url=sessie.checkout_url)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_signup_endpoint.py -v'"
```

Expected: all PASS. `tests/test_stripe_webhook_endpoint.py` will now fail (its `_leg_aanmelding_vast` helper calls `maak_aanmelding` without the new required arguments) — that's expected and fixed in Task 8, not here.

- [ ] **Step 6: Commit**

```bash
git add serving/schemas.py serving/app.py tests/test_signup_endpoint.py
git commit -m "feat: collect KVK-nummer and seat/vestiging counts at signup, price accordingly"
```

---

### Task 8: `POST /webhooks/stripe` — transfer KVK/seat/vestiging to the new organisation

**Files:**
- Modify: `serving/app.py`
- Test: `tests/test_stripe_webhook_endpoint.py`

**Interfaces:**
- Consumes: `bootstrap_organisatie(..., kvk_nummer=, ingekochte_leden=, ingekochte_winkels=)` (Task 3), the `aanmeldingen` row's `.kvk_nummer`/`.aantal_leden`/`.aantal_winkels`/`.was_kvk_herhaling` (Task 1).

- [ ] **Step 1: Write the failing tests**

First, fix the existing `_leg_aanmelding_vast` helper in `tests/test_stripe_webhook_endpoint.py` (it calls `maak_aanmelding` without the new required arguments, which now breaks every test in this file):

```python
def _leg_aanmelding_vast(engine, sessie_id="cs_test_123", kvk_nummer="12345678", was_kvk_herhaling=False):
    hash_hex, salt_hex = hash_key("correct-paard")
    return maak_aanmelding(
        engine, organisatie_naam="Bakkerij De Vries", organisatie_slug="bakkerij-de-vries",
        email="devries@voorbeeld.nl", wachtwoord_hash=hash_hex, wachtwoord_salt=salt_hex,
        stripe_checkout_session_id=sessie_id, kvk_nummer=kvk_nummer, aantal_leden=1, aantal_winkels=1,
        was_kvk_herhaling=was_kvk_herhaling,
    )
```

Then add the new tests:

```python
def test_checkout_completed_zet_kvk_en_aantallen_op_organisatie(tmp_path, monkeypatch):
    from sqlalchemy import select

    from db.schema import organisaties

    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _leg_aanmelding_vast(engine)
    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _checkout_completed_event("cs_test_123"))

    resp = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})

    assert resp.status_code == 200, resp.text
    aanmelding = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    with engine.connect() as conn:
        org = conn.execute(select(organisaties).where(organisaties.c.id == aanmelding.organisatie_id)).one()
    assert org.kvk_nummer == "12345678"
    assert org.ingekochte_leden == 1
    assert org.ingekochte_winkels == 1


def test_checkout_completed_herhaalde_kvk_zet_trial_verloopt_op_op_none(tmp_path, monkeypatch):
    from sqlalchemy import select

    from db.schema import organisaties

    module, client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _leg_aanmelding_vast(engine, was_kvk_herhaling=True)
    monkeypatch.setattr(module, "lees_webhook_event", lambda **kw: _checkout_completed_event("cs_test_123"))

    resp = client.post("/webhooks/stripe", content=b"ruwe-payload", headers={"stripe-signature": "t=1,v1=geldig"})

    assert resp.status_code == 200, resp.text
    aanmelding = haal_aanmelding_bij_sessie(engine, "cs_test_123")
    with engine.connect() as conn:
        org = conn.execute(select(organisaties).where(organisaties.c.id == aanmelding.organisatie_id)).one()
    assert org.trial_verloopt_op is None

    from db.organisaties import is_in_proefperiode
    assert is_in_proefperiode(engine, aanmelding.organisatie_id) is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_stripe_webhook_endpoint.py -v'"
```

Expected: the two new tests FAIL (organisation has no `kvk_nummer`/`ingekochte_leden`/`ingekochte_winkels` yet, and `trial_verloopt_op` is always set to +14 days regardless of `was_kvk_herhaling`). Every pre-existing test in this file should now PASS again once the `_leg_aanmelding_vast` fix from Step 1 is in place (confirm this).

- [ ] **Step 3: Implement**

In `serving/app.py`'s webhook handler, change:

```python
    with tenants_db.begin() as conn:
        org_id = bootstrap_organisatie(
            tenants_db, naam=aanmelding.organisatie_naam, slug=aanmelding.organisatie_slug, store_ids=[], conn=conn,
            trial_verloopt_op=datetime.now(timezone.utc) + timedelta(days=SIGNUP_PROEFPERIODE_DAGEN),
        )
```

to:

```python
    with tenants_db.begin() as conn:
        org_id = bootstrap_organisatie(
            tenants_db, naam=aanmelding.organisatie_naam, slug=aanmelding.organisatie_slug, store_ids=[], conn=conn,
            trial_verloopt_op=(
                None if aanmelding.was_kvk_herhaling
                else datetime.now(timezone.utc) + timedelta(days=SIGNUP_PROEFPERIODE_DAGEN)
            ),
            kvk_nummer=aanmelding.kvk_nummer,
            ingekochte_leden=aanmelding.aantal_leden,
            ingekochte_winkels=aanmelding.aantal_winkels,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_stripe_webhook_endpoint.py -v'"
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add serving/app.py tests/test_stripe_webhook_endpoint.py
git commit -m "feat: transfer KVK-nummer and purchased counts to the organisation, skip trial on repeat KVK"
```

---

### Task 9: `POST /gebruikers` seat cap + `GET /me` purchased-count exposure

**Files:**
- Modify: `serving/app.py`
- Test: `tests/test_gebruikers_endpoint.py`

**Interfaces:**
- Consumes: `db_organisaties.haal_ingekochte_leden`/`haal_ingekochte_winkels` (Task 2), `db_gebruikers.aantal_actieve_gebruikers` (Task 4).
- Produces: `GET /me` response gains `"ingekochte_leden"` and `"ingekochte_winkels"` keys (both `Optional[int]`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_gebruikers_endpoint.py`. First check whether the existing `_bouw_gebruikers_omgeving` fixture's `bootstrap_organisatie` calls need a variant with `ingekochte_leden` set — add these new tests using direct calls with the extra kwarg:

```python
def test_gebruiker_aanmaken_binnen_limiet_lukt(tmp_path, monkeypatch):
    from db.bootstrap import bootstrap_organisatie
    from db.gebruikers import maak_gebruiker

    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    # _bouw_gebruikers_omgeving bouwt org_a/org_b al op zonder limiet; deze
    # test heeft een eigen organisatie nodig mét een limiet, dus die apart
    # aanmaken via dezelfde engine — zie hoe _bouw_gebruikers_omgeving zijn
    # engine teruggeeft, of bouw een eigen kleine omgeving zoals hieronder.
```

Given the exact shape of `_bouw_gebruikers_omgeving` (whether it returns just a `client` or `(client, engine)`) needs to be re-checked at implementation time — read the current top of `tests/test_gebruikers_endpoint.py` first. Write the tests against whatever it actually returns, following this logic:

```python
def test_gebruiker_aanmaken_op_limiet_geeft_403(tmp_path, monkeypatch):
    # Bouw een eigen kleine omgeving (niet de gedeelde org_a/org_b fixture)
    # zodat ingekochte_leden expliciet op 1 gezet kan worden.
    import numpy as np
    import pandas as pd
    from fastapi.testclient import TestClient

    from db.bootstrap import bootstrap_organisatie
    from db.gebruikers import maak_gebruiker
    from db.schema import maak_database
    from training import artifact, train
    import importlib
    import sys

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
    org_id = bootstrap_organisatie(engine, naam="Beperkte Klant", slug="beperkte-klant", store_ids=[], ingekochte_leden=1)
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar-beperkt@klant.nl", wachtwoord="wachtwoord-1", rol="eigenaar")

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
    client = TestClient(module.app)

    _inloggen(client, "eigenaar-beperkt@klant.nl", "wachtwoord-1")
    resp = client.post("/gebruikers", json={"email": "nieuw-lid@klant.nl", "wachtwoord": "een-nieuw-wachtwoord"})

    assert resp.status_code == 403


def test_gebruiker_aanmaken_zonder_limiet_lukt_altijd(tmp_path, monkeypatch):
    # De gedeelde org_a-fixture in _bouw_gebruikers_omgeving heeft geen
    # ingekochte_leden gezet (NULL) — dit is exact het "geen limiet"-pad
    # dat elke organisatie van vóór dit prijsmodel gebruikt. Hergebruikt
    # de bestaande fixture rechtstreeks.
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.post("/gebruikers", json={"email": "weer-een-lid@klant.nl", "wachtwoord": "een-nieuw-wachtwoord"})

    assert resp.status_code == 201


def test_me_toont_ingekochte_aantallen(tmp_path, monkeypatch):
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.get("/me")

    assert resp.status_code == 200
    assert resp.json()["ingekochte_leden"] is None
    assert resp.json()["ingekochte_winkels"] is None
```

(Adjust the two tests that reuse `_bouw_gebruikers_omgeving` if that helper actually returns `(client, engine)` rather than just `client` — check the top of the file, already partially read during planning: it returns `TestClient(module.app)` alone based on the excerpt seen, so `client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)` is correct, but re-verify against the file's current state before running.)

- [ ] **Step 2: Run tests to verify they fail**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_gebruikers_endpoint.py -v'"
```

Expected: `test_gebruiker_aanmaken_op_limiet_geeft_403` FAILS (currently 201, no cap enforced), `test_me_toont_ingekochte_aantallen` FAILS with a `KeyError`/missing-key assertion (the `/me` response doesn't have these keys yet). `test_gebruiker_aanmaken_zonder_limiet_lukt_altijd` should already PASS (no behavior change for the NULL case) — confirm it does, as a sanity check that the eventual cap-check correctly no-ops on NULL.

- [ ] **Step 3: Implement**

In `serving/app.py`, change `POST /gebruikers`:

```python
@app.post("/gebruikers", response_model=GebruikerResponse, status_code=201)
def gebruiker_aanmaken(
    verzoek: GebruikerAanmakenVerzoek, eigenaar: GeauthenticeerdeGebruiker = Depends(vereis_eigenaar)
) -> GebruikerResponse:
    # NULL ingekochte_leden = geen limiet — elke organisatie van vóór dit
    # prijsmodel (en elke handmatig aangemaakte organisatie) heeft dit, en
    # moet nooit geblokkeerd worden.
    ingekochte_leden = db_organisaties.haal_ingekochte_leden(tenants_db, eigenaar.organisatie_id)
    if ingekochte_leden is not None:
        huidig_aantal = db_gebruikers.aantal_actieve_gebruikers(tenants_db, eigenaar.organisatie_id)
        if huidig_aantal >= ingekochte_leden:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Je hebt het maximum aantal teamleden ({ingekochte_leden}) bereikt voor je huidige "
                    "abonnement. Neem contact op om uit te breiden."
                ),
            )
    # Een zelf-aangemaakte gebruiker is altijd "lid" — een tweede eigenaar
    # toevoegen kan alleen via db/gebruikers_cli.py (operatorhandeling),
    # om onbedoelde privilege-escalatie via dit endpoint uit te sluiten.
    try:
        gebruiker_id = db_gebruikers.maak_gebruiker(
            tenants_db, organisatie_id=eigenaar.organisatie_id, email=verzoek.email, wachtwoord=verzoek.wachtwoord
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail=f"E-mailadres {verzoek.email} is al in gebruik.")
    return GebruikerResponse(id=gebruiker_id, email=verzoek.email, rol="lid", actief=True)
```

And `GET /me`:

```python
@app.get("/me")
def me(gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)) -> dict:
    trial_verloopt_op = db_organisaties.haal_trial_verloopt_op(tenants_db, gebruiker.organisatie_id)
    return {
        "email": gebruiker.email, "rol": gebruiker.rol, "organisatie_id": gebruiker.organisatie_id,
        "in_proefperiode": db_organisaties.is_in_proefperiode(tenants_db, gebruiker.organisatie_id),
        "trial_verloopt_op": trial_verloopt_op.date().isoformat() if trial_verloopt_op else None,
        "ingekochte_leden": db_organisaties.haal_ingekochte_leden(tenants_db, gebruiker.organisatie_id),
        "ingekochte_winkels": db_organisaties.haal_ingekochte_winkels(tenants_db, gebruiker.organisatie_id),
    }
```

- [ ] **Step 4: Run tests to verify they pass, then run the full backend suite**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_gebruikers_endpoint.py -v'"
```

Expected: all PASS. Then run the complete suite to confirm zero regressions across every backend file touched by Tasks 1-9:

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest -q'"
```

Expected: PASS, no failures. Clean up the remote scratch dir if it's become root-owned before the next rsync: `ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/data alpine sh -c 'rm -rf /data/*'"`.

- [ ] **Step 5: Commit**

```bash
git add serving/app.py tests/test_gebruikers_endpoint.py
git commit -m "feat: enforce purchased seat limit on POST /gebruikers, expose it on GET /me"
```

---

### Task 10: Frontend — signup screen (KVK, teamleden, vestigingen, live price)

**Files:**
- Modify: `dashboard/signup.html`
- Modify: `dashboard/account.js`

**Interfaces:**
- Consumes: `POST /signup` now requires `kvk_nummer` and accepts `aantal_leden`/`aantal_winkels` (Task 7).

- [ ] **Step 1: Update `dashboard/signup.html`**

Change the header copy (fixing the pre-existing "€ 49" and "7 dagen" inconsistencies at the same time — the real values are €29 and 14 days):

```html
      <p class="sub">14 dagen gratis proberen, daarna vanaf € 29 per maand. Geen sales-gesprek, geen installatie.</p>
```

Add the new fields to the form, right after the existing `organisatie-naam` field block and before the `email` field block:

```html
    <div class="veld">
      <label for="kvk-nummer">KVK-nummer</label>
      <input type="text" id="kvk-nummer" required pattern="\d{8}" maxlength="8" inputmode="numeric" autocomplete="off">
    </div>
```

Add the two count fields and the price preview right after the existing `wachtwoord` field block and before the submit button:

```html
    <div class="veld">
      <label for="aantal-leden">Totaal aantal gebruikers (inclusief jezelf)</label>
      <input type="number" id="aantal-leden" min="1" value="1" required>
    </div>
    <div class="veld">
      <div class="veld-label-rij">
        <label for="aantal-winkels">Aantal vestigingen</label>
        <details class="info">
          <summary aria-label="Wat betekent vestigingen?">?</summary>
          <p class="info-inhoud">De eerste vestiging is gratis inbegrepen. Elke vestiging daarna kost € 10 per maand extra.</p>
        </details>
      </div>
      <input type="number" id="aantal-winkels" min="1" value="1" required>
    </div>
    <p class="sub" id="prijs-preview" style="margin:0 0 8px;">Totaal: € 29 per maand</p>
```

- [ ] **Step 2: Update `dashboard/account.js`**

Change `meldAan()` to send the three new fields:

```javascript
async function meldAan(organisatieNaam, email, wachtwoord, kvkNummer, aantalLeden, aantalWinkels) {
  const resp = await fetch(`${API_BASIS}/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      organisatie_naam: organisatieNaam, email, wachtwoord,
      kvk_nummer: kvkNummer, aantal_leden: aantalLeden, aantal_winkels: aantalWinkels,
    }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Aanmelden mislukt (${resp.status})`);
  }
  return resp.json();
}
```

Change `initSignupPagina()` to wire up the live price preview and pass the new fields through on submit:

```javascript
function initSignupPagina() {
  const form = document.getElementById("signup-form");
  if (!form) return;

  const werkPrijsPreviewBij = () => {
    const ledenEl = document.getElementById("aantal-leden");
    const winkelsEl = document.getElementById("aantal-winkels");
    const previewEl = document.getElementById("prijs-preview");
    if (!ledenEl || !winkelsEl || !previewEl) return;
    const leden = Math.max(1, parseInt(ledenEl.value, 10) || 1);
    const winkels = Math.max(1, parseInt(winkelsEl.value, 10) || 1);
    const totaal = 29 + (leden - 1) * 5 + (winkels - 1) * 10;
    previewEl.textContent = `Totaal: ${euro.format(totaal)} per maand`;
  };
  document.getElementById("aantal-leden")?.addEventListener("input", werkPrijsPreviewBij);
  document.getElementById("aantal-winkels")?.addEventListener("input", werkPrijsPreviewBij);
  werkPrijsPreviewBij();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("signup-knop");
    knop.disabled = true;
    toonFout("fout", "");
    try {
      const { checkout_url: checkoutUrl } = await meldAan(
        document.getElementById("organisatie-naam").value,
        document.getElementById("email").value,
        document.getElementById("wachtwoord").value,
        document.getElementById("kvk-nummer").value,
        parseInt(document.getElementById("aantal-leden").value, 10) || 1,
        parseInt(document.getElementById("aantal-winkels").value, 10) || 1,
      );
      window.location.href = checkoutUrl;
    } catch (e) {
      toonFout("fout", e.message);
      knop.disabled = false;
    }
  });
}
```

(`euro` is already declared as a top-level `const` near the top of `account.js` — reuse it directly, do not redeclare it. `toonFout` is likewise an existing shared helper already used elsewhere in this file.)

- [ ] **Step 3: Deploy and browser-verify**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/signup.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/account.js \
    job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome, navigate to `https://forecasting-demo.tessar.nl/signup.html` and verify:
- The header now reads "14 dagen gratis proberen, daarna vanaf € 29 per maand."
- KVK-nummer, "Totaal aantal gebruikers," and "Aantal vestigingen" fields are all present, defaulting to empty/1/1.
- Changing "Totaal aantal gebruikers" to 3 and "Aantal vestigingen" to 2 updates the price line to "Totaal: € 49 per maand" (29 + 2×5 + 1×10) immediately, with no page reload.
- Entering a non-8-digit value in KVK-nummer and submitting shows the browser's native validation message (the `pattern`/`required` attributes) rather than silently submitting.
- Do NOT complete the actual Stripe checkout (entering card data is out of scope) — verifying the form builds a checkout session at all (e.g. that submitting with valid data navigates away to a `checkout.stripe.com` URL) is sufficient; do not go further than confirming that redirect happens.

- [ ] **Step 4: Commit**

```bash
git add dashboard/signup.html dashboard/account.js
git commit -m "feat: collect KVK-nummer and seat/vestiging counts on signup, live price preview"
```

---

### Task 11: Frontend — purchased-counts display on `team.html`

**Files:**
- Modify: `dashboard/team.html`
- Modify: `dashboard/account.js`

**Interfaces:**
- Consumes: `GET /me`'s new `ingekochte_leden`/`ingekochte_winkels` fields (Task 9).

- [ ] **Step 1: Add the markup to `dashboard/team.html`**

Insert right after the existing `<div class="kaart"><div class="teamlijst" id="teamlijst"></div></div>` block (the team-member list card):

```html
  <p class="sub" id="abonnement-aantallen" hidden style="margin:0 0 20px;"></p>
```

- [ ] **Step 2: Populate it in `dashboard/account.js`'s `initTeamPagina()`**

Find the line `initPortfolioSidebar(me);` inside `initTeamPagina()` and add right after it:

```javascript
  initPortfolioSidebar(me);
  if (me.ingekochte_leden !== null || me.ingekochte_winkels !== null) {
    const el = document.getElementById("abonnement-aantallen");
    if (el) {
      const delen = [];
      if (me.ingekochte_leden !== null) delen.push(`${me.ingekochte_leden} teamleden`);
      if (me.ingekochte_winkels !== null) delen.push(`${me.ingekochte_winkels} vestigingen`);
      el.textContent = `Abonnement: ${delen.join(", ")} inbegrepen.`;
      el.hidden = false;
    }
  }
```

(`me` here is the same object `initTeamPagina()` already receives from `haalMe()` earlier in the function — no new fetch needed.)

- [ ] **Step 3: Deploy and browser-verify**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/team.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/account.js \
    job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome, log into `https://forecasting-demo.tessar.nl/team.html` with the existing demo account (`info@tessar.nl` or similar already-authenticated session) — since that organisation was manually bootstrapped, `ingekochte_leden`/`ingekochte_winkels` are both `NULL`, so the new line should stay hidden (confirm no "Abonnement: ..." text appears, and no layout shift/empty gap from the hidden element). This is the expected, correct behavior for every pre-existing organisation — a self-serve organisation created after this ships is the only way to see the line populated, which cannot be verified against live production for the same Stripe-payment reason noted throughout this plan; trust the code path instead (it mirrors the already-verified `/me` test from Task 9).

- [ ] **Step 4: Commit**

```bash
git add dashboard/team.html dashboard/account.js
git commit -m "feat: show purchased seat/vestiging counts on Team beheren"
```

---

### Task 12: Manual Stripe setup + production deploy + final verification

**Files:** none (Stripe dashboard configuration + deploy + verification only)

**Interfaces:** none new — this task activates everything built in Tasks 1-11 together.

- [ ] **Step 1: Create the two new Stripe Price objects (manual, Stripe dashboard)**

This is a manual step for you (the product owner) to do directly in the Stripe dashboard, not something to script — creating live billing prices isn't a code change:
1. Create a recurring monthly Price of €5, e.g. named "Extra teamlid." Note its Price ID (`price_...`).
2. Create a recurring monthly Price of €10, e.g. named "Extra vestiging." Note its Price ID (`price_...`).
3. Confirm the existing base Price (`STRIPE_PRICE_ID` already configured on the server) is actually set to €29/month — if it's still set to whatever produced the "€49" text on the old signup page, update it (or create a new €29 Price and point `STRIPE_PRICE_ID` at it instead, which avoids retroactively changing the price of any already-subscribed customer's existing subscription).

- [ ] **Step 2: Set the two new environment variables on the server**

```bash
ssh job@157.90.244.24 "grep -q '^STRIPE_PRICE_ID_EXTRA_LID=' /home/job/forecasting-demo/deploy/.env && echo PRESENT || echo ABSENT"
```

If `ABSENT` (expected on first run), append both (replace the placeholder values with the real Price IDs from Step 1 — do this interactively, don't hardcode real Price IDs into this plan document):

```bash
ssh job@157.90.244.24 "cat >> /home/job/forecasting-demo/deploy/.env" <<'EOF'
STRIPE_PRICE_ID_EXTRA_LID=price_REPLACE_ME
STRIPE_PRICE_ID_EXTRA_WINKEL=price_REPLACE_ME
EOF
```

(Note: `.env` lives at `deploy/.env`, not the repo-root-level path — confirmed during the earlier onboarding feature's deploy, the same correction applies here.)

- [ ] **Step 3: Deploy the backend**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/db/schema.py \
    /Users/hamdeco/development/hamdoun/forecasting/db/aanmeldingen.py \
    /Users/hamdeco/development/hamdoun/forecasting/db/organisaties.py \
    /Users/hamdeco/development/hamdoun/forecasting/db/bootstrap.py \
    /Users/hamdeco/development/hamdoun/forecasting/db/gebruikers.py \
    job@157.90.244.24:/home/job/forecasting-demo/db/

scp /Users/hamdeco/development/hamdoun/forecasting/serving/betaalintegratie.py \
    /Users/hamdeco/development/hamdoun/forecasting/serving/config.py \
    /Users/hamdeco/development/hamdoun/forecasting/serving/schemas.py \
    /Users/hamdeco/development/hamdoun/forecasting/serving/app.py \
    job@157.90.244.24:/home/job/forecasting-demo/serving/
```

```bash
ssh job@157.90.244.24 "cd /home/job/forecasting-demo/deploy && docker compose build api && docker compose up -d"
```

- [ ] **Step 4: Smoke-test**

```bash
ssh job@157.90.244.24 "docker compose -f /home/job/forecasting-demo/deploy/docker-compose.yml ps"
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://forecasting-demo.tessar.nl/signup \
  -H "Content-Type: application/json" \
  -d '{"organisatie_naam":"Smoketest","email":"smoketest-plan-check@example.invalid","wachtwoord":"smoketest-wachtwoord"}'
```

Expected: container `Up (healthy)`; the curl (missing `kvk_nummer`) returns `422` — confirming the new required field is actually enforced in production, not just in tests.

- [ ] **Step 5: Deploy the frontend (if Tasks 10-11 weren't already deployed individually)**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/signup.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/account.js \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/team.html \
    job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

- [ ] **Step 6: Final live verification**

Using claude-in-chrome:
- Confirm `signup.html` shows the corrected copy and live price preview (same checks as Task 10 Step 3, re-run against the now-fully-deployed backend).
- Confirm the existing demo account's `team.html` still shows no purchased-counts line (Task 11 Step 3, re-confirmed).
- Do not attempt to complete a real signup end-to-end (Stripe payment) — this remains out of scope for the reasons stated throughout this plan.

- [ ] **Step 7: Update project memory**

Once verified, record in memory (per the existing `forecasting_toolkit_audit_roadmap` memory) that the per-seat/per-vestiging pricing model has shipped, including the corrected €29 base price and the now-resolved copy inconsistencies on `signup.html`, and that the separate "audit which features should be Premium-gated" request from the same conversation remains open as its own future spec.

---

## Self-Review

**Spec coverage:** Every spec section maps to a task — `kvk_nummer`/`aantal_leden`/`aantal_winkels` collection and pricing (Tasks 1, 6, 7, 10), Stripe line-item/trial mechanics (Task 5), KVK-repeat detection and trial-skip (Tasks 2, 7, 8), seat cap enforcement with NULL-means-unlimited (Tasks 2, 4, 9), purchased-count display (Task 9, 11), the corrected €29 base price and stale-copy fixes (Task 10), and the manual Stripe-dashboard + deploy sequence (Task 12).

**Placeholder scan:** No TBD/TODO markers. Task 12 Step 2 intentionally uses `price_REPLACE_ME` as a literal placeholder value — this is correct and unavoidable (a real Stripe Price ID doesn't exist until Step 1's manual dashboard action creates it), not a plan-writing shortcut; the step's own text makes clear this must be replaced interactively, not committed as-is. Task 9 Step 1 flags one spot (`_bouw_gebruikers_omgeving`'s exact return shape) to re-verify against the live file rather than blindly trust the plan's transcription — this is a deliberate, narrow "confirm before use" instruction, not a vague placeholder.

**Type consistency:** `haal_ingekochte_leden`/`haal_ingekochte_winkels` (Task 2) return `Optional[int]`, matched exactly by their usage in Task 9's `/gebruikers` and `/me` handlers. `maak_checkout_sessie`'s `extra_line_items: Optional[list[dict]]` (Task 5) matches exactly how Task 7's `/signup` builds and passes it. `bootstrap_organisatie`'s new `kvk_nummer`/`ingekochte_leden`/`ingekochte_winkels` parameters (Task 3) match exactly how Task 8's webhook handler calls it. `maak_aanmelding`'s new required parameters (Task 1) match exactly how Task 7's `/signup` and Task 8's test helper call it.
