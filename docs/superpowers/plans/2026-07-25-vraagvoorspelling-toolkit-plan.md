# Vraagvoorspelling-toolkit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable, locally-runnable toolkit (pipeline → training → serving API → dashboard) that delivers retail demand forecasting with real accuracy numbers, built and validated on the Rossmann Store Sales dataset, ready to later become a website demo and to be reused for real client data.

**Architecture:** Three decoupled parts. `pipeline/` + `training/` run offline/batch and produce a versioned artifact (models + bundled per-store history + accuracy metrics). `serving/` is a thin FastAPI app that loads one explicitly pinned artifact version and never trains. `dashboard/` is a static, Tessar-styled frontend that only talks to the API over a configurable base URL — the piece designed to drop onto the live website later with minimal change.

**Tech Stack:** Python 3.11, pandas, XGBoost (quantile regression, `reg:quantileerror`), FastAPI + Uvicorn, `cryptography` (AES-256-GCM), slowapi (rate limiting), pytest, Docker Compose.

## Global Constraints

- All new code lives in a new `forecasting/` subdirectory at the root of the existing `hamdoun` (Tessar) repo — a monorepo layout choice, not a new repo. GitHub Pages will passively serve these source files as static text once pushed; that's an accepted, deferred concern for the later live-deployment phase, not something this plan solves.
- XGBoost must be `>=2.0` (quantile regression via `objective="reg:quantileerror"` requires it). If that's ever unavailable in a build environment, LightGBM (`objective="quantile"`) is the documented fallback — noted in README.md, not implemented unless it's actually needed.
- Never a silent fallback for security-critical config: missing `MODEL_VERSION`, missing API-keys file, missing encryption key when encryption is toggled on, or an unset `CORS_ALLOWED_ORIGINS` must all fail loudly, never default to something permissive.
- RMSPE calculations must exclude rows where actual sales are 0 (closed-store days) — never divide by zero.
- Three independently-trained quantile models (p10/p50/p90) do not guarantee ordering — every place that returns them to a caller must sort first.
- No shuffled train/validation/test splits — time-ordered only, with an explicit leakage assertion.
- File permissions: chmod 600 on any file containing hashed keys, audit-log entries, or model artifacts.
- Dataset: Rossmann Store Sales is for building/validating the method only, never redistributed raw; the live demo (out of scope for this plan) will show calibrated/synthetic or anonymized values instead.

---

## Task 1: Project scaffolding

**Files:**
- Create: `forecasting/requirements.in`
- Create: `forecasting/.env.example`
- Create: `forecasting/.gitignore`
- Create: `forecasting/pytest.ini`
- Create: `forecasting/security/__init__.py`
- Create: `forecasting/pipeline/__init__.py`
- Create: `forecasting/training/__init__.py`
- Create: `forecasting/serving/__init__.py`
- Create: `forecasting/tests/__init__.py`

**Interfaces:**
- Produces: a working Python environment where `pytest` run from `forecasting/` resolves `from pipeline...`, `from training...`, `from serving...`, `from security...` imports without `PYTHONPATH` tricks.

- [ ] **Step 1: Create the directory structure and empty package markers**

```bash
mkdir -p forecasting/{security,pipeline,training,serving,dashboard,tests,data,models}
touch forecasting/security/__init__.py forecasting/pipeline/__init__.py \
      forecasting/training/__init__.py forecasting/serving/__init__.py \
      forecasting/tests/__init__.py
```

- [ ] **Step 2: Write `forecasting/requirements.in`**

```
fastapi>=0.115
uvicorn[standard]>=0.32
pydantic>=2.9
xgboost>=2.0
pandas>=2.2
numpy>=1.26
pyarrow>=17.0
cryptography>=43.0
python-dotenv>=1.0
slowapi>=0.1.9
httpx>=0.27
pytest>=8.0
```

- [ ] **Step 3: Write `forecasting/pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 4: Write `forecasting/.env.example`**

```
MODEL_VERSION=
MODELS_DIR=models
API_KEYS_FILE=api_keys.json
AUDIT_LOG_FILE=audit.log
CORS_ALLOWED_ORIGINS=
FORECASTING_ENCRYPT_AT_REST=false
FORECASTING_ENCRYPTIE_SLEUTEL=
RATE_LIMIT_PER_MINUUT=60
```

- [ ] **Step 5: Write `forecasting/.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
data/*.csv
models/*
!models/.gitkeep
api_keys.json
audit.log
```

```bash
touch forecasting/models/.gitkeep
```

- [ ] **Step 6: Create a virtualenv, install, and freeze pinned versions**

```bash
cd forecasting
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.in
pip freeze > requirements.txt
```

Expected: `requirements.txt` now contains exact pinned versions of everything in `requirements.in` plus transitive dependencies. Confirm `xgboost` in it is `>=2.0`:

```bash
grep -i xgboost requirements.txt
```

Expected: a version string starting with `2.` or higher. If it's lower than 2.0, stop and note this in README.md's "known risks" section — the quantile-regression tasks later in this plan will need the LightGBM fallback instead.

- [ ] **Step 7: Verify pytest resolves imports**

```bash
echo "def test_placeholder(): assert True" > tests/test_placeholder.py
pytest -v
rm tests/test_placeholder.py
```

Expected: 1 passed.

- [ ] **Step 8: Commit**

```bash
git add forecasting/requirements.in forecasting/requirements.txt forecasting/.env.example \
        forecasting/.gitignore forecasting/pytest.ini forecasting/*/__init__.py forecasting/models/.gitkeep
git commit -m "forecasting: scaffold project structure and pinned dependencies"
```

---

## Task 2: Encryption module (`security/encryptie.py`)

Ported from Certo's `encryptie.py` (protocolchecker project) — same algorithm (AES-256-GCM), same hard-fail-on-missing-key philosophy.

**Files:**
- Create: `forecasting/security/encryptie.py`
- Test: `forecasting/tests/test_encryptie.py`

**Interfaces:**
- Produces: `laad_sleutel() -> bytes`, `genereer_sleutel() -> str`, `versleutel(data: bytes, sleutel: bytes | None = None) -> bytes`, `ontsleutel(data: bytes, sleutel: bytes | None = None) -> bytes`, `schrijf_bestand(pad: Path, data: bytes) -> None`, `lees_bestand(pad: Path) -> bytes`. Env var: `FORECASTING_ENCRYPTIE_SLEUTEL`.

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_encryptie.py
import base64
import os

import pytest
from cryptography.exceptions import InvalidTag

from security import encryptie


@pytest.fixture(autouse=True)
def _reset_cache():
    encryptie._sleutel_cache = None
    yield
    encryptie._sleutel_cache = None


def test_versleutel_ontsleutel_round_trip(monkeypatch):
    monkeypatch.setenv(encryptie.SLEUTEL_ENV_VAR, encryptie.genereer_sleutel())
    origineel = b"geheime inhoud"
    versleuteld = encryptie.versleutel(origineel)
    assert encryptie.ontsleutel(versleuteld) == origineel


def test_ontsleutel_detecteert_manipulatie(monkeypatch):
    monkeypatch.setenv(encryptie.SLEUTEL_ENV_VAR, encryptie.genereer_sleutel())
    versleuteld = bytearray(encryptie.versleutel(b"data"))
    versleuteld[-1] ^= 0xFF
    with pytest.raises(InvalidTag):
        encryptie.ontsleutel(bytes(versleuteld))


def test_laad_sleutel_faalt_hard_zonder_env(monkeypatch):
    monkeypatch.delenv(encryptie.SLEUTEL_ENV_VAR, raising=False)
    with pytest.raises(RuntimeError, match=encryptie.SLEUTEL_ENV_VAR):
        encryptie.laad_sleutel()


def test_laad_sleutel_faalt_hard_bij_verkeerde_lengte(monkeypatch):
    monkeypatch.setenv(encryptie.SLEUTEL_ENV_VAR, base64.b64encode(b"te kort").decode())
    with pytest.raises(RuntimeError, match="moet"):
        encryptie.laad_sleutel()


def test_laad_sleutel_faalt_hard_bij_ongeldige_base64(monkeypatch):
    monkeypatch.setenv(encryptie.SLEUTEL_ENV_VAR, "!!!niet-base64!!!")
    with pytest.raises(RuntimeError, match="base64"):
        encryptie.laad_sleutel()


def test_schrijf_en_lees_bestand_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv(encryptie.SLEUTEL_ENV_VAR, encryptie.genereer_sleutel())
    pad = tmp_path / "geheim.bin"
    encryptie.schrijf_bestand(pad, b"payload")
    assert encryptie.lees_bestand(pad) == b"payload"
    assert oct(pad.stat().st_mode)[-3:] == "600"


def test_lees_bestand_faalt_hard_zonder_magic_kop(tmp_path, monkeypatch):
    monkeypatch.setenv(encryptie.SLEUTEL_ENV_VAR, encryptie.genereer_sleutel())
    pad = tmp_path / "plat.bin"
    pad.write_bytes(b"gewoon platte tekst, geen encryptie")
    with pytest.raises(RuntimeError, match="verwachte versleutelde formaat"):
        encryptie.lees_bestand(pad)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_encryptie.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'security.encryptie'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/security/encryptie.py
"""Versleuteling in rust voor de forecasting-toolkit's audit-log en
modelartefacten.

AES-256-GCM via de cryptography-package: authenticated encryption — een
gewijzigd of corrupt bestand geeft bij het ontsleutelen een harde fout
(InvalidTag) in plaats van stilzwijgend verkeerde data.

Direct afgeleid van Certo's encryptie.py (protocolchecker-project): zelfde
algoritme, zelfde hard-fail-op-ontbrekende-sleutel-filosofie.

Sleutel genereren:  python3 -m security.encryptie genereer-sleutel
"""
from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path

from cryptography.exceptions import InvalidTag  # noqa: F401 (voor aanroepers die 'm willen vangen)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SLEUTEL_ENV_VAR = "FORECASTING_ENCRYPTIE_SLEUTEL"
SLEUTEL_LENGTE = 32  # AES-256
NONCE_LENGTE = 12
MAGIC = b"TSRFCST1"

_sleutel_cache: bytes | None = None


def laad_sleutel() -> bytes:
    """Leest en cachet de encryptiesleutel uit de omgeving. Faalt hard als de
    sleutel ontbreekt of de verkeerde lengte heeft — nooit een stille
    fallback, dat zou onopgemerkt tot onleesbare data leiden."""
    global _sleutel_cache
    if _sleutel_cache is not None:
        return _sleutel_cache

    ruw = os.environ.get(SLEUTEL_ENV_VAR)
    if not ruw:
        raise RuntimeError(
            f"{SLEUTEL_ENV_VAR} ontbreekt in de omgeving. Genereer een sleutel met:\n"
            "    python3 -m security.encryptie genereer-sleutel"
        )
    try:
        sleutel = base64.b64decode(ruw, validate=True)
    except Exception as e:
        raise RuntimeError(f"{SLEUTEL_ENV_VAR} is geen geldige base64-waarde: {e}")
    if len(sleutel) != SLEUTEL_LENGTE:
        raise RuntimeError(
            f"{SLEUTEL_ENV_VAR} moet {SLEUTEL_LENGTE} bytes zijn na base64-decodering, "
            f"kreeg {len(sleutel)}."
        )
    _sleutel_cache = sleutel
    return sleutel


def genereer_sleutel() -> str:
    """Genereert een nieuwe willekeurige sleutel, als base64-string."""
    return base64.b64encode(secrets.token_bytes(SLEUTEL_LENGTE)).decode("ascii")


def versleutel(data: bytes, sleutel: bytes | None = None) -> bytes:
    if sleutel is None:
        sleutel = laad_sleutel()
    nonce = os.urandom(NONCE_LENGTE)
    ciphertext = AESGCM(sleutel).encrypt(nonce, data, None)
    return nonce + ciphertext


def ontsleutel(data: bytes, sleutel: bytes | None = None) -> bytes:
    if sleutel is None:
        sleutel = laad_sleutel()
    nonce, ciphertext = data[:NONCE_LENGTE], data[NONCE_LENGTE:]
    return AESGCM(sleutel).decrypt(nonce, ciphertext, None)


def schrijf_bestand(pad: Path, data: bytes) -> None:
    """Versleutelt en schrijft data weg, met MAGIC-kop en chmod 600."""
    pad.write_bytes(MAGIC + versleutel(data))
    try:
        os.chmod(pad, 0o600)
    except OSError:
        pass


def lees_bestand(pad: Path) -> bytes:
    """Leest en ontsleutelt een bestand geschreven met schrijf_bestand()."""
    ruw = pad.read_bytes()
    if not ruw.startswith(MAGIC):
        raise RuntimeError(f"{pad} staat niet in het verwachte versleutelde formaat.")
    return ontsleutel(ruw[len(MAGIC):])


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "genereer-sleutel":
        print(genereer_sleutel())
    else:
        print("Gebruik: python3 -m security.encryptie genereer-sleutel")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_encryptie.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/security/encryptie.py forecasting/tests/test_encryptie.py
git commit -m "forecasting: add AES-256-GCM encryption module (ported from Certo)"
```

---

## Task 3: API-key management (`security/api_keys.py`)

**Files:**
- Create: `forecasting/security/api_keys.py`
- Test: `forecasting/tests/test_api_keys.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `hash_key(ruwe_key: str, salt: bytes | None = None) -> tuple[str, str]`, `verifieer_key(ruwe_key: str, hash_hex: str, salt_hex: str) -> bool`, `laad_keys(pad: Path) -> dict`, `voeg_key_toe(pad: Path, naam: str, ruwe_key: str) -> None`, `vind_key_naam(pad: Path, ruwe_key: str) -> str | None`.

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_api_keys.py
from security import api_keys


def test_hash_en_verifieer_round_trip():
    hash_hex, salt_hex = api_keys.hash_key("geheime-key-123")
    assert api_keys.verifieer_key("geheime-key-123", hash_hex, salt_hex) is True


def test_verifieer_wijst_verkeerde_key_af():
    hash_hex, salt_hex = api_keys.hash_key("geheime-key-123")
    assert api_keys.verifieer_key("andere-key", hash_hex, salt_hex) is False


def test_verifieer_faalt_niet_hard_bij_corrupte_salt():
    hash_hex, _ = api_keys.hash_key("geheime-key-123")
    assert api_keys.verifieer_key("geheime-key-123", hash_hex, "niet-hex") is False


def test_laad_keys_geeft_lege_dict_als_bestand_ontbreekt(tmp_path):
    assert api_keys.laad_keys(tmp_path / "ontbreekt.json") == {}


def test_voeg_key_toe_en_vind_key_naam(tmp_path):
    pad = tmp_path / "api_keys.json"
    api_keys.voeg_key_toe(pad, "klant-a", "key-voor-klant-a")
    api_keys.voeg_key_toe(pad, "klant-b", "key-voor-klant-b")

    assert api_keys.vind_key_naam(pad, "key-voor-klant-a") == "klant-a"
    assert api_keys.vind_key_naam(pad, "key-voor-klant-b") == "klant-b"
    assert api_keys.vind_key_naam(pad, "onbekende-key") is None


def test_voeg_key_toe_zet_chmod_600(tmp_path):
    pad = tmp_path / "api_keys.json"
    api_keys.voeg_key_toe(pad, "klant-a", "key-voor-klant-a")
    assert oct(pad.stat().st_mode)[-3:] == "600"


def test_intrekken_van_een_key_raakt_andere_keys_niet(tmp_path):
    pad = tmp_path / "api_keys.json"
    api_keys.voeg_key_toe(pad, "klant-a", "key-a")
    api_keys.voeg_key_toe(pad, "klant-b", "key-b")

    keys = api_keys.laad_keys(pad)
    del keys["klant-a"]
    import json
    pad.write_text(json.dumps(keys), encoding="utf-8")

    assert api_keys.vind_key_naam(pad, "key-a") is None
    assert api_keys.vind_key_naam(pad, "key-b") == "klant-b"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_api_keys.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'security.api_keys'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/security/api_keys.py
"""API-key-beheer: keys worden nooit in platte tekst opgeslagen, alleen als
PBKDF2-HMAC-SHA256-hash met een per-key unieke salt — zelfde aanpak als
Certo's wachtwoordhashing. Zo kan één klantintegratie worden ingetrokken
zonder de rest te raken."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

HASH_ITERATIES = 600_000


def hash_key(ruwe_key: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", ruwe_key.encode("utf-8"), salt, HASH_ITERATIES, dklen=32)
    return digest.hex(), salt.hex()


def verifieer_key(ruwe_key: str, hash_hex: str, salt_hex: str) -> bool:
    try:
        berekend, _ = hash_key(ruwe_key, bytes.fromhex(salt_hex))
    except (ValueError, TypeError):
        return False
    return secrets.compare_digest(berekend, hash_hex)


def laad_keys(pad: Path) -> dict:
    if not pad.exists():
        return {}
    return json.loads(pad.read_text(encoding="utf-8"))


def voeg_key_toe(pad: Path, naam: str, ruwe_key: str) -> None:
    keys = laad_keys(pad)
    hash_hex, salt_hex = hash_key(ruwe_key)
    keys[naam] = {"hash": hash_hex, "salt": salt_hex}
    pad.write_text(json.dumps(keys, indent=2), encoding="utf-8")
    try:
        os.chmod(pad, 0o600)
    except OSError:
        pass


def vind_key_naam(pad: Path, ruwe_key: str) -> str | None:
    """Zoekt welke genoemde key overeenkomt met ruwe_key. Geeft None terug
    als geen enkele overeenkomt (of het bestand leeg/ontbrekend is)."""
    keys = laad_keys(pad)
    for naam, info in keys.items():
        if verifieer_key(ruwe_key, info["hash"], info["salt"]):
            return naam
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_api_keys.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/security/api_keys.py forecasting/tests/test_api_keys.py
git commit -m "forecasting: add hashed API-key storage and verification"
```

---

## Task 4: Audit logging (`security/audit.py`)

**Files:**
- Create: `forecasting/security/audit.py`
- Test: `forecasting/tests/test_audit.py`

**Interfaces:**
- Consumes: `security.encryptie.versleutel`, `security.encryptie.ontsleutel` (Task 2).
- Produces: `log(pad: Path, event: dict, versleuteld: bool) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_audit.py
import base64
import json

import pytest

from security import audit, encryptie


def test_log_schrijft_leesbare_regel_zonder_encryptie(tmp_path):
    pad = tmp_path / "audit.log"
    audit.log(pad, {"key": "klant-a", "store_id": 1}, versleuteld=False)
    regel = pad.read_text(encoding="utf-8").strip()
    data = json.loads(regel)
    assert data["key"] == "klant-a"
    assert data["store_id"] == 1
    assert "tijdstip" in data


def test_log_schrijft_versleutelde_regel(tmp_path, monkeypatch):
    monkeypatch.setenv(encryptie.SLEUTEL_ENV_VAR, encryptie.genereer_sleutel())
    encryptie._sleutel_cache = None
    pad = tmp_path / "audit.log"
    audit.log(pad, {"key": "klant-a"}, versleuteld=True)
    regel = pad.read_text(encoding="utf-8").strip()

    with pytest.raises(json.JSONDecodeError):
        json.loads(regel)

    ontsleuteld = json.loads(encryptie.ontsleutel(base64.b64decode(regel)))
    assert ontsleuteld["key"] == "klant-a"


def test_log_voegt_toe_zonder_bestaande_regels_te_lezen(tmp_path):
    pad = tmp_path / "audit.log"
    audit.log(pad, {"key": "klant-a"}, versleuteld=False)
    audit.log(pad, {"key": "klant-b"}, versleuteld=False)
    regels = pad.read_text(encoding="utf-8").strip().splitlines()
    assert len(regels) == 2
    assert json.loads(regels[0])["key"] == "klant-a"
    assert json.loads(regels[1])["key"] == "klant-b"


def test_log_zet_chmod_600(tmp_path):
    pad = tmp_path / "audit.log"
    audit.log(pad, {"key": "klant-a"}, versleuteld=False)
    assert oct(pad.stat().st_mode)[-3:] == "600"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_audit.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'security.audit'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/security/audit.py
"""Audit-logging voor de forecasting-API: staat altijd aan (wie vroeg wat,
wanneer), alleen de versleuteling ervan is toggle-baar via config. Elke regel
heeft zijn eigen nonce, dus toevoegen hoeft nooit het hele bestand te lezen."""
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

from security import encryptie


def log(pad: Path, event: dict, versleuteld: bool) -> None:
    """Voegt één regel toe aan het audit-logbestand. `event` bevat nooit
    ruwe gevoelige payloads, alleen metadata (key-naam, store_id, horizon,
    statuscode, latency)."""
    regel = {"tijdstip": time.time(), **event}
    plat = json.dumps(regel, ensure_ascii=False)

    bestond_al = pad.exists()
    with pad.open("a", encoding="utf-8") as f:
        if versleuteld:
            f.write(base64.b64encode(encryptie.versleutel(plat.encode("utf-8"))).decode("ascii") + "\n")
        else:
            f.write(plat + "\n")

    if not bestond_al:
        try:
            os.chmod(pad, 0o600)
        except OSError:
            pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_audit.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/security/audit.py forecasting/tests/test_audit.py
git commit -m "forecasting: add always-on, optionally-encrypted audit logging"
```

---

## Task 5: Data ingestion (`pipeline/ingest.py`)

**Files:**
- Create: `forecasting/pipeline/ingest.py`
- Test: `forecasting/tests/test_ingest.py`

**Interfaces:**
- Produces: `laad_train(pad: Path) -> pd.DataFrame`, `laad_winkels(pad: Path) -> pd.DataFrame`, `laad_test(pad: Path) -> pd.DataFrame`, `samenvoegen(transacties: pd.DataFrame, winkels: pd.DataFrame) -> pd.DataFrame`.

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_ingest.py
import pandas as pd
import pytest

from pipeline import ingest


def _schrijf_csv(tmp_path, naam, inhoud):
    pad = tmp_path / naam
    pad.write_text(inhoud, encoding="utf-8")
    return pad


def test_laad_train_leest_stateholiday_als_string(tmp_path):
    pad = _schrijf_csv(
        tmp_path, "train.csv",
        "Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday\n"
        "1,1,2015-07-01,1000,200,1,1,0,0\n"
        "1,2,2015-07-02,1100,210,1,0,a,0\n",
    )
    df = ingest.laad_train(pad)
    assert df["StateHoliday"].dtype == object
    assert set(df["StateHoliday"]) == {"0", "a"}


def test_laad_train_faalt_hard_bij_ontbrekende_kolom(tmp_path):
    pad = _schrijf_csv(tmp_path, "train.csv", "Store,Date,Sales\n1,2015-07-01,1000\n")
    with pytest.raises(ValueError, match="mist verplichte kolommen"):
        ingest.laad_train(pad)


def test_laad_train_sorteert_op_winkel_en_datum(tmp_path):
    pad = _schrijf_csv(
        tmp_path, "train.csv",
        "Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday\n"
        "2,1,2015-07-01,500,100,1,0,0,0\n"
        "1,3,2015-07-03,1200,220,1,0,0,0\n"
        "1,1,2015-07-01,1000,200,1,1,0,0\n",
    )
    df = ingest.laad_train(pad)
    assert list(df["Store"]) == [1, 1, 2]
    assert list(df["Date"]) == list(pd.to_datetime(["2015-07-01", "2015-07-03", "2015-07-01"]))


def test_laad_test_vult_ontbrekende_open_met_1(tmp_path):
    pad = _schrijf_csv(
        tmp_path, "test.csv",
        "Store,DayOfWeek,Date,Open,Promo,StateHoliday,SchoolHoliday\n"
        "1,1,2015-08-01,,0,0,0\n"
        "1,2,2015-08-02,0,0,0,0\n",
    )
    df = ingest.laad_test(pad)
    assert df["Open"].tolist() == [1, 0]
    assert not df["Open"].isna().any()


def test_laad_winkels_faalt_hard_bij_ontbrekende_kolom(tmp_path):
    pad = _schrijf_csv(tmp_path, "store.csv", "Store,StoreType\n1,a\n")
    with pytest.raises(ValueError, match="mist verplichte kolommen"):
        ingest.laad_winkels(pad)


def test_samenvoegen_koppelt_winkelmetadata(tmp_path):
    transacties = pd.DataFrame({
        "Store": [1, 2], "DayOfWeek": [1, 1],
        "Date": pd.to_datetime(["2015-07-01", "2015-07-01"]),
        "Sales": [1000, 500], "Customers": [200, 100], "Open": [1, 1],
        "Promo": [0, 0], "StateHoliday": ["0", "0"], "SchoolHoliday": [0, 0],
    })
    winkels = pd.DataFrame({
        "Store": [1, 2], "StoreType": ["a", "b"], "Assortment": ["a", "a"],
        "CompetitionDistance": [500.0, 1200.0],
    })
    samengevoegd = ingest.samenvoegen(transacties, winkels)
    assert samengevoegd.loc[samengevoegd["Store"] == 1, "CompetitionDistance"].iloc[0] == 500.0


def test_samenvoegen_faalt_hard_bij_ontbrekende_winkelmetadata():
    transacties = pd.DataFrame({
        "Store": [1, 99], "DayOfWeek": [1, 1],
        "Date": pd.to_datetime(["2015-07-01", "2015-07-01"]),
        "Sales": [1000, 500], "Customers": [200, 100], "Open": [1, 1],
        "Promo": [0, 0], "StateHoliday": ["0", "0"], "SchoolHoliday": [0, 0],
    })
    winkels = pd.DataFrame({
        "Store": [1], "StoreType": ["a"], "Assortment": ["a"], "CompetitionDistance": [500.0],
    })
    with pytest.raises(ValueError, match="geen winkelmetadata"):
        ingest.samenvoegen(transacties, winkels)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_ingest.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.ingest'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/pipeline/ingest.py
"""Inlezen en samenvoegen van de brondata, met expliciete afhandeling van
bekende dataquirks (zie design-spec, sectie Data & model)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

VERPLICHTE_TRAIN_KOLOMMEN = {
    "Store", "DayOfWeek", "Date", "Sales", "Customers",
    "Open", "Promo", "StateHoliday", "SchoolHoliday",
}
VERPLICHTE_STORE_KOLOMMEN = {
    "Store", "StoreType", "Assortment", "CompetitionDistance",
}


def laad_train(pad: Path) -> pd.DataFrame:
    """Leest train.csv. StateHoliday expliciet als string inlezen: het
    bestand mixt '0' (geen feestdag) met 'a'/'b'/'c' (feestdagtypes), en
    zonder dtype-hint leidt pandas hier soms een gemengd int/str-type uit
    af, wat verderop stille bugs geeft in de featureconstructie."""
    df = pd.read_csv(pad, dtype={"StateHoliday": str}, parse_dates=["Date"])
    ontbrekend = VERPLICHTE_TRAIN_KOLOMMEN - set(df.columns)
    if ontbrekend:
        raise ValueError(f"train.csv mist verplichte kolommen: {sorted(ontbrekend)}")
    return df.sort_values(["Store", "Date"]).reset_index(drop=True)


def laad_winkels(pad: Path) -> pd.DataFrame:
    df = pd.read_csv(pad)
    ontbrekend = VERPLICHTE_STORE_KOLOMMEN - set(df.columns)
    if ontbrekend:
        raise ValueError(f"store.csv mist verplichte kolommen: {sorted(ontbrekend)}")
    return df


def laad_test(pad: Path) -> pd.DataFrame:
    """Leest test.csv. Een klein aantal rijen mist de Open-waarde; die vullen
    we expliciet met 1 (open) — de aanname die de Rossmann-competitie zelf
    hanteert voor deze ontbrekende waarden. Nooit stilzwijgend als NaN laten
    doorlopen naar de featureconstructie."""
    df = pd.read_csv(pad, dtype={"StateHoliday": str}, parse_dates=["Date"])
    if "Open" in df.columns and df["Open"].isna().any():
        df["Open"] = df["Open"].fillna(1).astype(int)
    return df.sort_values(["Store", "Date"]).reset_index(drop=True)


def samenvoegen(transacties: pd.DataFrame, winkels: pd.DataFrame) -> pd.DataFrame:
    df = transacties.merge(winkels, on="Store", how="left", validate="many_to_one")
    ontbrekende_metadata = df["StoreType"].isna().sum()
    if ontbrekende_metadata:
        raise ValueError(
            f"{ontbrekende_metadata} rijen hebben geen winkelmetadata na de merge — "
            "controleer of store.csv alle Store-ID's uit de transacties bevat."
        )
    return df
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_ingest.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/pipeline/ingest.py forecasting/tests/test_ingest.py
git commit -m "forecasting: add data ingestion with explicit dataquirk handling"
```

---

## Task 6: Feature engineering (`pipeline/features.py`)

**Files:**
- Create: `forecasting/pipeline/features.py`
- Test: `forecasting/tests/test_features.py`

**Interfaces:**
- Produces: `LAG_DAGEN = (7, 14, 21)`, `ROLLING_VENSTERS = (7, 28)`, `MAX_HISTORIE_DAGEN = 28`, `voeg_kalenderfeatures_toe(df) -> df`, `voeg_lag_features_toe(df) -> df`, `bouw_features(df) -> df`, `controleer_geen_lekkage(train, validatie) -> None` (raises `AssertionError`/`ValueError`).

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_features.py
import numpy as np
import pandas as pd
import pytest

from pipeline import features


def _reeks(store, start, n, waarde_per_dag):
    datums = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({"Store": store, "Date": datums, "Sales": waarde_per_dag, "Open": 1})


def test_lag_feature_gebruikt_juiste_historische_waarde():
    df = pd.DataFrame({
        "Store": [1] * 10,
        "Date": pd.date_range("2015-01-01", periods=10, freq="D"),
        "Sales": list(range(100, 1100, 100)),
        "Open": [1] * 10,
    })
    resultaat = features.voeg_lag_features_toe(df)
    # dag 8 (index 7, Sales=800) moet als lag_7 de Sales van dag 1 (100) hebben
    assert resultaat.iloc[7]["omzet_lag_7"] == 100


def test_lag_feature_lekt_niet_tussen_winkels():
    df = pd.concat([
        _reeks(1, "2015-01-01", 10, 1000),
        _reeks(2, "2015-01-01", 10, 5000),
    ], ignore_index=True)
    resultaat = features.voeg_lag_features_toe(df)
    winkel_2_rijen = resultaat[resultaat["Store"] == 2]
    # de lag-waarden voor winkel 2 mogen nooit 1000 zijn (dat is winkel 1's omzet)
    assert not (winkel_2_rijen["omzet_lag_7"] == 1000).any()


def test_rolling_feature_respecteert_min_periods():
    df = _reeks(1, "2015-01-01", 5, 1000)
    resultaat = features.voeg_lag_features_toe(df)
    # venster van 7 dagen kan met maar 5 historische rijen nooit gevuld zijn
    assert resultaat["omzet_rolling_gemiddeld_7"].isna().all()


def test_rolling_feature_sluit_de_dag_zelf_uit():
    df = pd.DataFrame({
        "Store": [1] * 8,
        "Date": pd.date_range("2015-01-01", periods=8, freq="D"),
        "Sales": [100, 100, 100, 100, 100, 100, 100, 999999],
        "Open": [1] * 8,
    })
    resultaat = features.voeg_lag_features_toe(df)
    # rolling_7 op de laatste dag moet het gemiddelde zijn van de 7 dagen ervoor (allemaal 100),
    # niet beïnvloed door de 999999 van de dag zelf
    assert resultaat.iloc[-1]["omzet_rolling_gemiddeld_7"] == 100


def test_controleer_geen_lekkage_accepteert_correcte_scheiding():
    train = pd.DataFrame({"Date": pd.to_datetime(["2015-01-01", "2015-01-05"])})
    validatie = pd.DataFrame({"Date": pd.to_datetime(["2015-01-10"])})
    features.controleer_geen_lekkage(train, validatie)  # mag niet raisen


def test_controleer_geen_lekkage_verwerpt_overlap():
    train = pd.DataFrame({"Date": pd.to_datetime(["2015-01-01", "2015-01-15"])})
    validatie = pd.DataFrame({"Date": pd.to_datetime(["2015-01-10"])})
    with pytest.raises(AssertionError, match="lekkage"):
        features.controleer_geen_lekkage(train, validatie)


def test_controleer_geen_lekkage_verwerpt_lege_set():
    with pytest.raises(ValueError):
        features.controleer_geen_lekkage(pd.DataFrame({"Date": []}), pd.DataFrame({"Date": [pd.Timestamp("2015-01-01")]}))


def test_bouw_features_voegt_kalender_en_lag_toe():
    df = _reeks(1, "2015-01-01", 30, 1000)
    resultaat = features.bouw_features(df)
    for kolom in ("Jaar", "Maand", "Dag", "Weeknummer", "omzet_lag_7", "omzet_rolling_gemiddeld_28"):
        assert kolom in resultaat.columns
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_features.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.features'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/pipeline/features.py
"""Featureconstructie voor het vraagvoorspellingsmodel.

Elke feature die uit het verleden van dezelfde winkel wordt afgeleid (lags,
rolling-gemiddeldes) moet strikt vóór de voorspeldatum liggen. groupby +
shift/transform garandeert dat een lag nooit de eigen rij (of een latere
rij), en nooit een andere winkel, gebruikt."""
from __future__ import annotations

import pandas as pd

LAG_DAGEN = (7, 14, 21)
ROLLING_VENSTERS = (7, 28)
MAX_HISTORIE_DAGEN = max(max(LAG_DAGEN), max(ROLLING_VENSTERS))


def voeg_kalenderfeatures_toe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Jaar"] = df["Date"].dt.year
    df["Maand"] = df["Date"].dt.month
    df["Dag"] = df["Date"].dt.day
    df["Weeknummer"] = df["Date"].dt.isocalendar().week.astype(int)
    return df


def voeg_lag_features_toe(df: pd.DataFrame) -> pd.DataFrame:
    """Voegt lag- en rolling-window-features toe, per winkel apart berekend.
    Rijen waarop de vereiste laghistorie ontbreekt (het begin van elke
    winkelreeks) krijgen NaN — die worden later expliciet uit de
    trainingsset verwijderd, niet stilzwijgend op 0 gezet."""
    df = df.sort_values(["Store", "Date"]).copy()
    for n in LAG_DAGEN:
        df[f"omzet_lag_{n}"] = df.groupby("Store")["Sales"].shift(n)
    for venster in ROLLING_VENSTERS:
        # .transform() garandeert output uitgelijnd met de originele index,
        # per groep berekend — voorkomt dat een rolling-window per ongeluk
        # over de grens van twee winkels heen kijkt.
        df[f"omzet_rolling_gemiddeld_{venster}"] = df.groupby("Store")["Sales"].transform(
            lambda s, w=venster: s.shift(1).rolling(w, min_periods=w).mean()
        )
    return df


def controleer_geen_lekkage(train: pd.DataFrame, validatie: pd.DataFrame) -> None:
    """Harde assertion: de trainingsperiode moet volledig vóór de
    validatieperiode liggen. Faalt de trainingsrun hard als dat niet zo is,
    in plaats van een opgeblazen nauwkeurigheidscijfer te laten ontstaan
    door toekomstige data die in de training is geslopen."""
    if train.empty or validatie.empty:
        raise ValueError("Train- of validatieset is leeg — kan lekkage niet controleren.")
    laatste_train_datum = train["Date"].max()
    eerste_validatie_datum = validatie["Date"].min()
    if laatste_train_datum >= eerste_validatie_datum:
        raise AssertionError(
            f"Data-lekkage: laatste trainingsdatum ({laatste_train_datum.date()}) ligt niet "
            f"vóór de eerste validatiedatum ({eerste_validatie_datum.date()})."
        )


def bouw_features(df: pd.DataFrame) -> pd.DataFrame:
    df = voeg_kalenderfeatures_toe(df)
    df = voeg_lag_features_toe(df)
    return df
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_features.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/pipeline/features.py forecasting/tests/test_features.py
git commit -m "forecasting: add calendar/lag/rolling features with leakage guard"
```

---

## Task 7: Time-ordered split (`pipeline/split.py`)

**Files:**
- Create: `forecasting/pipeline/split.py`
- Test: `forecasting/tests/test_split.py`

**Interfaces:**
- Consumes: `pipeline.features.controleer_geen_lekkage` (Task 6).
- Produces: `walk_forward_split(df, validatie_dagen: int, test_dagen: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]`.

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_split.py
import pandas as pd
import pytest

from pipeline import split


def _dataset(n_dagen=100):
    datums = pd.date_range("2015-01-01", periods=n_dagen, freq="D")
    return pd.DataFrame({"Store": 1, "Date": datums, "Sales": range(n_dagen)})


def test_split_grenzen_kloppen():
    df = _dataset(100)
    train, validatie, test = split.walk_forward_split(df, validatie_dagen=10, test_dagen=10)
    assert train["Date"].max() < validatie["Date"].min()
    assert validatie["Date"].max() < test["Date"].min()
    assert test["Date"].max() == df["Date"].max()


def test_split_dagaantallen_kloppen():
    df = _dataset(100)
    train, validatie, test = split.walk_forward_split(df, validatie_dagen=10, test_dagen=10)
    assert len(test) == 10
    assert len(validatie) == 10
    assert len(train) == 80


def test_split_geen_overlap_tussen_sets():
    df = _dataset(60)
    train, validatie, test = split.walk_forward_split(df, validatie_dagen=7, test_dagen=7)
    alle_datums = pd.concat([train["Date"], validatie["Date"], test["Date"]])
    assert alle_datums.is_unique
    assert len(alle_datums) == len(df)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_split.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.split'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/pipeline/split.py
"""Tijd-geordende walk-forward split: nooit shufflen, dat zou data-lekkage
veroorzaken bij een tijdreeksprobleem."""
from __future__ import annotations

import pandas as pd

from pipeline.features import controleer_geen_lekkage


def walk_forward_split(
    df: pd.DataFrame, validatie_dagen: int, test_dagen: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Splitst df in train/validatie/test op basis van de laatste
    `validatie_dagen + test_dagen` kalenderdagen, niet op rijaantal — anders
    krijgen winkels met meer transacties een groter aandeel van de
    validatie-/testperiode dan winkels met minder."""
    laatste_datum = df["Date"].max()
    test_start = laatste_datum - pd.Timedelta(days=test_dagen - 1)
    validatie_start = test_start - pd.Timedelta(days=validatie_dagen)

    train = df[df["Date"] < validatie_start]
    validatie = df[(df["Date"] >= validatie_start) & (df["Date"] < test_start)]
    test = df[df["Date"] >= test_start]

    controleer_geen_lekkage(train, validatie)
    controleer_geen_lekkage(validatie, test)

    return train, validatie, test
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_split.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/pipeline/split.py forecasting/tests/test_split.py
git commit -m "forecasting: add calendar-day-based walk-forward split"
```

---

## Task 8: Quantile model training (`training/train.py`)

**Files:**
- Create: `forecasting/training/train.py`
- Test: `forecasting/tests/test_train.py`

**Interfaces:**
- Produces: `KWANTIELEN = (0.1, 0.5, 0.9)`, `FEATURE_KOLOMMEN: list[str]`, `DOEL_KOLOM = "Sales"`, `bereid_trainset_voor(df) -> df`, `train_kwantielmodel(train, kwantiel: float) -> xgb.XGBRegressor`, `train_alle_kwantielen(train) -> dict[float, xgb.XGBRegressor]`.

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_train.py
import numpy as np
import pandas as pd
import pytest

from training import train


def _synthetische_trainset(n=300):
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "Store": rng.integers(1, 4, n),
        "DayOfWeek": rng.integers(1, 8, n),
        "Promo": rng.integers(0, 2, n),
        "SchoolHoliday": rng.integers(0, 2, n),
        "Jaar": 2015,
        "Maand": rng.integers(1, 13, n),
        "Dag": rng.integers(1, 28, n),
        "Weeknummer": rng.integers(1, 53, n),
        "CompetitionDistance": rng.uniform(100, 5000, n),
        "omzet_lag_7": rng.uniform(500, 2000, n),
        "omzet_lag_14": rng.uniform(500, 2000, n),
        "omzet_lag_21": rng.uniform(500, 2000, n),
        "omzet_rolling_gemiddeld_7": rng.uniform(500, 2000, n),
        "omzet_rolling_gemiddeld_28": rng.uniform(500, 2000, n),
        "Open": 1,
    })
    df["Sales"] = df["omzet_rolling_gemiddeld_7"] + rng.normal(0, 50, n)
    return df


def test_bereid_trainset_voor_verwijdert_onvolledige_rijen():
    df = _synthetische_trainset(20)
    df.loc[0, "omzet_lag_7"] = np.nan
    resultaat = train.bereid_trainset_voor(df)
    assert len(resultaat) == 19


def test_bereid_trainset_voor_verwijdert_gesloten_winkeldagen():
    df = _synthetische_trainset(20)
    df.loc[0, "Open"] = 0
    resultaat = train.bereid_trainset_voor(df)
    assert len(resultaat) == 19


def test_train_alle_kwantielen_faalt_hard_op_lege_trainset():
    lege_df = _synthetische_trainset(5)
    lege_df["Open"] = 0
    with pytest.raises(ValueError, match="leeg"):
        train.train_alle_kwantielen(lege_df)


def test_train_alle_kwantielen_geeft_drie_modellen():
    df = _synthetische_trainset(300)
    modellen = train.train_alle_kwantielen(df)
    assert set(modellen.keys()) == {0.1, 0.5, 0.9}


def test_getraind_model_geeft_eindige_voorspellingen():
    df = _synthetische_trainset(300)
    modellen = train.train_alle_kwantielen(df)
    voorspeld = modellen[0.5].predict(df[train.FEATURE_KOLOMMEN].iloc[:5])
    assert np.all(np.isfinite(voorspeld))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_train.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'training.train'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/training/train.py
"""Traint p10/p50/p90-modellen via XGBoost quantile regression.

Vereist XGBoost >=2.0 voor objective='reg:quantileerror' (zie
requirements.in en README.md voor de LightGBM-terugval als dat in de
buildomgeving niet beschikbaar blijkt)."""
from __future__ import annotations

import pandas as pd
import xgboost as xgb

KWANTIELEN = (0.1, 0.5, 0.9)

FEATURE_KOLOMMEN = [
    "Store", "DayOfWeek", "Promo", "SchoolHoliday", "Jaar", "Maand", "Dag",
    "Weeknummer", "CompetitionDistance",
    "omzet_lag_7", "omzet_lag_14", "omzet_lag_21",
    "omzet_rolling_gemiddeld_7", "omzet_rolling_gemiddeld_28",
]
DOEL_KOLOM = "Sales"


def bereid_trainset_voor(df: pd.DataFrame) -> pd.DataFrame:
    """Verwijdert rijen zonder volledige laghistorie (begin van elke
    winkelreeks) en gesloten-winkeldagen — een gesloten winkel heeft per
    definitie omzet 0, geen zinvol trainingssignaal voor vraag bij open
    winkels."""
    volledig = df.dropna(subset=FEATURE_KOLOMMEN + [DOEL_KOLOM])
    return volledig[volledig["Open"] == 1]


def train_kwantielmodel(train_df: pd.DataFrame, kwantiel: float) -> xgb.XGBRegressor:
    model = xgb.XGBRegressor(
        objective="reg:quantileerror",
        quantile_alpha=kwantiel,
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        random_state=42,
    )
    model.fit(train_df[FEATURE_KOLOMMEN], train_df[DOEL_KOLOM])
    return model


def train_alle_kwantielen(train_df: pd.DataFrame) -> dict[float, xgb.XGBRegressor]:
    voorbereid = bereid_trainset_voor(train_df)
    if voorbereid.empty:
        raise ValueError("Trainset is leeg na het verwijderen van onvolledige/gesloten rijen.")
    return {q: train_kwantielmodel(voorbereid, q) for q in KWANTIELEN}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_train.py -v
```

Expected: 5 passed. (If `reg:quantileerror` raises `XGBoostError: Unknown objective`, the installed XGBoost is below 2.0 — check `requirements.txt` from Task 1 Step 6 and upgrade before continuing; do not silently switch objectives.)

- [ ] **Step 5: Commit**

```bash
git add forecasting/training/train.py forecasting/tests/test_train.py
git commit -m "forecasting: add XGBoost p10/p50/p90 quantile training"
```

---

## Task 9: Evaluation — RMSPE, coverage, quantile sorting (`training/evaluate.py`)

**Files:**
- Create: `forecasting/training/evaluate.py`
- Test: `forecasting/tests/test_evaluate.py`

**Interfaces:**
- Consumes: `training.train.FEATURE_KOLOMMEN`, `training.train.DOEL_KOLOM` (Task 8).
- Produces: `rmspe(werkelijk, voorspeld) -> float`, `coverage(werkelijk, p10, p90) -> float`, `sorteer_kwantielen(p10, p50, p90) -> tuple[np.ndarray, np.ndarray, np.ndarray]`, `evalueer(modellen: dict[float, object], testset: pd.DataFrame) -> dict`.

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_evaluate.py
import numpy as np
import pandas as pd
import pytest

from training import evaluate


def test_rmspe_bekend_geval():
    werkelijk = pd.Series([100.0, 200.0])
    voorspeld = pd.Series([110.0, 180.0])
    # fouten: -10% en +10% -> sqrt(mean([0.01, 0.01])) = 0.1
    assert evaluate.rmspe(werkelijk, voorspeld) == pytest.approx(0.1, abs=1e-9)


def test_rmspe_sluit_nul_omzet_uit():
    werkelijk = pd.Series([0.0, 100.0])
    voorspeld = pd.Series([999.0, 110.0])
    # zonder de nul-rij uit te sluiten zou dit een ZeroDivisionError/inf geven
    resultaat = evaluate.rmspe(werkelijk, voorspeld)
    assert np.isfinite(resultaat)
    assert resultaat == pytest.approx(0.1, abs=1e-9)


def test_rmspe_faalt_hard_als_alles_nul_is():
    with pytest.raises(ValueError, match="RMSPE"):
        evaluate.rmspe(pd.Series([0.0, 0.0]), pd.Series([1.0, 2.0]))


def test_coverage_alles_binnen_band():
    werkelijk = pd.Series([5.0, 15.0, 25.0])
    p10 = pd.Series([0.0, 10.0, 20.0])
    p90 = pd.Series([10.0, 20.0, 30.0])
    assert evaluate.coverage(werkelijk, p10, p90) == pytest.approx(1.0)


def test_coverage_gedeeltelijk_buiten_band():
    werkelijk = pd.Series([5.0, 15.0, 35.0])
    p10 = pd.Series([0.0, 10.0, 20.0])
    p90 = pd.Series([10.0, 20.0, 30.0])
    assert evaluate.coverage(werkelijk, p10, p90) == pytest.approx(2 / 3)


def test_sorteer_kwantielen_corrigeert_kruising():
    p10, p50, p90 = evaluate.sorteer_kwantielen(
        np.array([50.0]), np.array([30.0]), np.array([70.0])
    )
    assert (p10[0], p50[0], p90[0]) == (30.0, 50.0, 70.0)


def test_sorteer_kwantielen_laat_correcte_volgorde_ongemoeid():
    p10, p50, p90 = evaluate.sorteer_kwantielen(
        np.array([10.0, 20.0]), np.array([50.0, 60.0]), np.array([90.0, 100.0])
    )
    assert list(p10) == [10.0, 20.0]
    assert list(p50) == [50.0, 60.0]
    assert list(p90) == [90.0, 100.0]


class _NepModel:
    def __init__(self, waarde):
        self.waarde = waarde

    def predict(self, X):
        return np.full(len(X), self.waarde)


def test_evalueer_geeft_rmspe_coverage_en_aantal():
    testset = pd.DataFrame({
        **{k: [1, 2, 3] for k in evaluate.FEATURE_KOLOMMEN if k != "Store"},
        "Store": [1, 1, 1],
        "Open": [1, 1, 1],
        evaluate.DOEL_KOLOM: [100.0, 100.0, 100.0],
    })
    modellen = {0.1: _NepModel(80.0), 0.5: _NepModel(100.0), 0.9: _NepModel(120.0)}
    resultaat = evaluate.evalueer(modellen, testset)
    assert resultaat["rmspe"] == pytest.approx(0.0, abs=1e-9)
    assert resultaat["coverage_p10_p90"] == pytest.approx(1.0)
    assert resultaat["n_observaties"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_evaluate.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'training.evaluate'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/training/evaluate.py
"""Evaluatie: RMSPE (met expliciete uitsluiting van nul-omzetdagen) en
coverage van de p10-p90-band."""
from __future__ import annotations

import numpy as np
import pandas as pd

from training.train import DOEL_KOLOM, FEATURE_KOLOMMEN


def rmspe(werkelijk: pd.Series, voorspeld: pd.Series) -> float:
    """Root Mean Squared Percentage Error, met dagen waarop de werkelijke
    omzet 0 is expliciet uitgesloten — anders deling door nul. De officiële
    Rossmann-competitiemetriek, dus vergelijkbaar met gepubliceerde
    benchmarks."""
    masker = werkelijk != 0
    if not masker.any():
        raise ValueError("Geen enkele rij met werkelijke omzet != 0 — kan RMSPE niet berekenen.")
    fout_percentage = (werkelijk[masker] - voorspeld[masker]) / werkelijk[masker]
    return float(np.sqrt(np.mean(np.square(fout_percentage))))


def coverage(werkelijk: pd.Series, p10: pd.Series, p90: pd.Series) -> float:
    """Aandeel werkelijke waarden dat binnen de p10-p90-band valt. Nominaal
    ~0.80 voor een goed gekalibreerd kwantielmodel — zonder deze check is de
    onzekerheidsband een ongefundeerde claim."""
    binnen_band = (werkelijk >= p10) & (werkelijk <= p90)
    return float(binnen_band.mean())


def sorteer_kwantielen(
    p10: np.ndarray, p50: np.ndarray, p90: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Drie onafhankelijk getrainde kwantielmodellen garanderen niet dat
    p10 <= p50 <= p90 per rij. Sorteert de drie waarden per rij zodat de
    teruggegeven band altijd logisch geordend is."""
    gestapeld = np.stack([p10, p50, p90], axis=0)
    gesorteerd = np.sort(gestapeld, axis=0)
    return gesorteerd[0], gesorteerd[1], gesorteerd[2]


def evalueer(modellen: dict[float, object], testset: pd.DataFrame) -> dict:
    voorbereid = testset.dropna(subset=FEATURE_KOLOMMEN + [DOEL_KOLOM])
    voorbereid = voorbereid[voorbereid["Open"] == 1]
    if voorbereid.empty:
        raise ValueError("Testset is leeg na filtering — kan niet evalueren.")

    ruwe_p10 = modellen[0.1].predict(voorbereid[FEATURE_KOLOMMEN])
    ruwe_p50 = modellen[0.5].predict(voorbereid[FEATURE_KOLOMMEN])
    ruwe_p90 = modellen[0.9].predict(voorbereid[FEATURE_KOLOMMEN])
    p10, p50, p90 = sorteer_kwantielen(ruwe_p10, ruwe_p50, ruwe_p90)

    return {
        "rmspe": rmspe(voorbereid[DOEL_KOLOM], pd.Series(p50, index=voorbereid.index)),
        "coverage_p10_p90": coverage(
            voorbereid[DOEL_KOLOM], pd.Series(p10, index=voorbereid.index), pd.Series(p90, index=voorbereid.index)
        ),
        "n_observaties": int(len(voorbereid)),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_evaluate.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/training/evaluate.py forecasting/tests/test_evaluate.py
git commit -m "forecasting: add RMSPE (zero-safe), coverage, and quantile sorting"
```

---

## Task 10: Versioned artifacts with optional at-rest encryption (`training/artifact.py`)

**Files:**
- Create: `forecasting/training/artifact.py`
- Test: `forecasting/tests/test_artifact.py`

**Interfaces:**
- Consumes: `pipeline.features.MAX_HISTORIE_DAGEN` (Task 6), `security.encryptie.schrijf_bestand`/`lees_bestand` (Task 2), `training.train.KWANTIELEN` (Task 8).
- Produces: `nieuwe_versie_naam() -> str`, `bewaar_historie(df, tot_en_met) -> pd.DataFrame`, `bewaar_winkel_metadata(winkels) -> pd.DataFrame`, `schrijf_artefact(basis_map, modellen, historie, winkel_metadata, metrics, trainingsperiode, gevalideerde_horizon_dagen, versleuteld) -> str`, `laad_artefact(basis_map, versie) -> dict` with keys `modellen`, `historie`, `winkel_metadata`, `metadata`.

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_artifact.py
import numpy as np
import pandas as pd
import pytest

from security import encryptie
from training import artifact, train


def _getraind_modellenset():
    n = 200
    rng = np.random.default_rng(0)
    df = pd.DataFrame({k: rng.uniform(0, 100, n) for k in train.FEATURE_KOLOMMEN})
    df["Sales"] = rng.uniform(500, 2000, n)
    df["Open"] = 1
    return train.train_alle_kwantielen(df)


def test_schrijf_en_laad_artefact_zonder_encryptie(tmp_path):
    modellen = _getraind_modellenset()
    historie = pd.DataFrame({
        "Store": [1, 1], "Date": pd.to_datetime(["2015-07-01", "2015-07-02"]),
        "Sales": [1000.0, 1100.0], "Open": [1, 1],
    })
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    metrics = {"rmspe": 0.12, "coverage_p10_p90": 0.81, "n_observaties": 1000}

    versie = artifact.schrijf_artefact(
        basis_map=tmp_path, modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        metrics=metrics, trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=48, versleuteld=False,
    )

    geladen = artifact.laad_artefact(tmp_path, versie)
    assert set(geladen["modellen"].keys()) == {0.1, 0.5, 0.9}
    assert geladen["historie"]["Sales"].tolist() == [1000.0, 1100.0]
    assert geladen["winkel_metadata"]["CompetitionDistance"].tolist() == [500.0]
    assert geladen["metadata"]["metrics"]["rmspe"] == 0.12
    assert geladen["metadata"]["gevalideerde_horizon_dagen"] == 48


def test_schrijf_en_laad_artefact_met_encryptie(tmp_path, monkeypatch):
    monkeypatch.setenv(encryptie.SLEUTEL_ENV_VAR, encryptie.genereer_sleutel())
    encryptie._sleutel_cache = None

    modellen = _getraind_modellenset()
    historie = pd.DataFrame({
        "Store": [1], "Date": pd.to_datetime(["2015-07-01"]), "Sales": [1000.0], "Open": [1],
    })
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    metrics = {"rmspe": 0.1, "coverage_p10_p90": 0.8, "n_observaties": 10}

    versie = artifact.schrijf_artefact(
        basis_map=tmp_path, modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        metrics=metrics, trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=48, versleuteld=True,
    )

    # rauwe bestandsinhoud mag geen leesbare JSON zijn
    ruwe_metadata = (tmp_path / versie / "metadata.json").read_bytes()
    assert ruwe_metadata.startswith(encryptie.MAGIC)

    geladen = artifact.laad_artefact(tmp_path, versie, versleuteld=True)
    assert geladen["metadata"]["metrics"]["rmspe"] == 0.1


def test_geschreven_bestanden_hebben_chmod_600(tmp_path):
    modellen = _getraind_modellenset()
    historie = pd.DataFrame({"Store": [1], "Date": pd.to_datetime(["2015-07-01"]), "Sales": [1000.0], "Open": [1]})
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    versie = artifact.schrijf_artefact(
        basis_map=tmp_path, modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.1, "coverage_p10_p90": 0.8, "n_observaties": 1},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=48, versleuteld=False,
    )
    for pad in (tmp_path / versie).iterdir():
        assert oct(pad.stat().st_mode)[-3:] == "600"


def test_laad_artefact_faalt_hard_bij_onbekende_versie(tmp_path):
    with pytest.raises(RuntimeError, match="bestaat niet"):
        artifact.laad_artefact(tmp_path, "geen-bestaande-versie")


def test_twee_snel_opeenvolgende_writes_krijgen_verschillende_versies(tmp_path, monkeypatch):
    modellen = _getraind_modellenset()
    historie = pd.DataFrame({"Store": [1], "Date": pd.to_datetime(["2015-07-01"]), "Sales": [1000.0], "Open": [1]})
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    monkeypatch.setattr(artifact, "nieuwe_versie_naam", lambda: "zelfde-tijdstip")

    versie_1 = artifact.schrijf_artefact(
        basis_map=tmp_path, modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.1, "coverage_p10_p90": 0.8, "n_observaties": 1},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=48, versleuteld=False,
    )
    versie_2 = artifact.schrijf_artefact(
        basis_map=tmp_path, modellen=modellen, historie=historie, winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.1, "coverage_p10_p90": 0.8, "n_observaties": 1},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=48, versleuteld=False,
    )
    assert versie_1 != versie_2


def test_bewaar_historie_beperkt_tot_buffer_venster():
    df = pd.DataFrame({
        "Store": [1] * 40,
        "Date": pd.date_range("2015-01-01", periods=40, freq="D"),
        "Sales": range(40),
        "Open": [1] * 40,
    })
    resultaat = artifact.bewaar_historie(df, tot_en_met=pd.Timestamp("2015-02-09"))
    verwachte_grens = pd.Timestamp("2015-02-09") - pd.Timedelta(days=artifact.HISTORIE_BUFFER_DAGEN)
    assert resultaat["Date"].min() > verwachte_grens
    assert resultaat["Date"].max() == pd.Timestamp("2015-02-09")


def test_bewaar_winkel_metadata_selecteert_juiste_kolommen():
    winkels = pd.DataFrame({
        "Store": [1, 2], "StoreType": ["a", "b"], "Assortment": ["a", "a"],
        "CompetitionDistance": [500.0, 1200.0],
    })
    resultaat = artifact.bewaar_winkel_metadata(winkels)
    assert list(resultaat.columns) == ["Store", "CompetitionDistance"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_artifact.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'training.artifact'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/training/artifact.py
"""Versioneren en wegschrijven van trainingsartefacten: de drie modellen, de
laatste historie per winkel (nodig om lag-features te reconstrueren bij een
voorspellingsverzoek), statische winkelmetadata, en metadata inclusief de
nauwkeurigheidscijfers. Encryptie is toggle-baar en geldt, indien aan, voor
alle bestanden in het artefact — nooit alleen voor een deel ervan."""
from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import xgboost as xgb

from pipeline.features import MAX_HISTORIE_DAGEN
from security import encryptie

HISTORIE_BUFFER_DAGEN = MAX_HISTORIE_DAGEN + 7  # marge boven de langste lag/rolling-vereiste


def nieuwe_versie_naam() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def bewaar_historie(df: pd.DataFrame, tot_en_met: pd.Timestamp) -> pd.DataFrame:
    """Bewaart per winkel alleen de laatste HISTORIE_BUFFER_DAGEN vóór
    `tot_en_met` — genoeg om lag-/rolling-features te reconstrueren, niet de
    volledige ruwe dataset."""
    grens = tot_en_met - pd.Timedelta(days=HISTORIE_BUFFER_DAGEN)
    return df[(df["Date"] > grens) & (df["Date"] <= tot_en_met)][
        ["Store", "Date", "Sales", "Open"]
    ].copy()


def bewaar_winkel_metadata(winkels: pd.DataFrame) -> pd.DataFrame:
    return winkels[["Store", "CompetitionDistance"]].copy()


def _schrijf(pad: Path, data: bytes, versleuteld: bool) -> None:
    if versleuteld:
        encryptie.schrijf_bestand(pad, data)
    else:
        pad.write_bytes(data)
        try:
            os.chmod(pad, 0o600)
        except OSError:
            pass


def _lees(pad: Path, versleuteld: bool) -> bytes:
    if versleuteld:
        return encryptie.lees_bestand(pad)
    return pad.read_bytes()


def schrijf_artefact(
    basis_map: Path,
    modellen: dict[float, xgb.XGBRegressor],
    historie: pd.DataFrame,
    winkel_metadata: pd.DataFrame,
    metrics: dict,
    trainingsperiode: tuple[pd.Timestamp, pd.Timestamp],
    gevalideerde_horizon_dagen: int,
    versleuteld: bool,
) -> str:
    """Schrijft een nieuw geversieerd artefact weg onder basis_map/<versie>/
    en geeft de versienaam terug. Bestaat de map al (zelfde seconde), dan
    wordt een teller toegevoegd om nooit een bestaand artefact te
    overschrijven."""
    basis_map.mkdir(parents=True, exist_ok=True)
    versie = nieuwe_versie_naam()
    doel = basis_map / versie
    teller = 1
    while doel.exists():
        teller += 1
        doel = basis_map / f"{versie}-{teller}"
    doel.mkdir(parents=True)

    for kwantiel, model in modellen.items():
        model_bytes = model.get_booster().save_raw(raw_format="json")
        _schrijf(doel / f"model_p{int(kwantiel * 100)}.json", bytes(model_bytes), versleuteld)

    historie_buffer = io.BytesIO()
    historie.to_parquet(historie_buffer, index=False)
    _schrijf(doel / "historie.parquet", historie_buffer.getvalue(), versleuteld)

    winkel_metadata_buffer = io.BytesIO()
    winkel_metadata.to_parquet(winkel_metadata_buffer, index=False)
    _schrijf(doel / "winkel_metadata.parquet", winkel_metadata_buffer.getvalue(), versleuteld)

    metadata = {
        "versie": doel.name,
        "aangemaakt_op": datetime.now(timezone.utc).isoformat(),
        "trainingsperiode_start": trainingsperiode[0].isoformat(),
        "trainingsperiode_eind": trainingsperiode[1].isoformat(),
        "gevalideerde_horizon_dagen": gevalideerde_horizon_dagen,
        "metrics": metrics,
    }
    _schrijf(doel / "metadata.json", json.dumps(metadata, indent=2).encode("utf-8"), versleuteld)

    return doel.name


def laad_artefact(basis_map: Path, versie: str, versleuteld: bool = False) -> dict:
    """Laadt een eerder weggeschreven artefact. Faalt hard als de versie niet
    bestaat of onvolledig is — nooit stilzwijgend een andere versie pakken."""
    doel = basis_map / versie
    if not doel.exists():
        raise RuntimeError(f"Modelversie '{versie}' bestaat niet onder {basis_map}.")

    modellen = {}
    for kwantiel in (0.1, 0.5, 0.9):
        model_pad = doel / f"model_p{int(kwantiel * 100)}.json"
        if not model_pad.exists():
            raise RuntimeError(f"Modelversie '{versie}' mist {model_pad.name}.")
        model_bytes = _lees(model_pad, versleuteld)
        model = xgb.XGBRegressor()
        model.load_model(bytearray(model_bytes))
        modellen[kwantiel] = model

    historie_pad = doel / "historie.parquet"
    winkel_metadata_pad = doel / "winkel_metadata.parquet"
    metadata_pad = doel / "metadata.json"
    for verplicht_pad in (historie_pad, winkel_metadata_pad, metadata_pad):
        if not verplicht_pad.exists():
            raise RuntimeError(f"Modelversie '{versie}' mist {verplicht_pad.name}.")

    return {
        "modellen": modellen,
        "historie": pd.read_parquet(io.BytesIO(_lees(historie_pad, versleuteld))),
        "winkel_metadata": pd.read_parquet(io.BytesIO(_lees(winkel_metadata_pad, versleuteld))),
        "metadata": json.loads(_lees(metadata_pad, versleuteld).decode("utf-8")),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_artifact.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/training/artifact.py forecasting/tests/test_artifact.py
git commit -m "forecasting: add versioned artifacts with optional at-rest encryption"
```

---

## Task 11: Training CLI (`training/cli.py`)

**Files:**
- Create: `forecasting/training/cli.py`
- Test: `forecasting/tests/test_cli.py`

**Interfaces:**
- Consumes: everything from Tasks 5–10.
- Produces: `main(argv: list[str] | None = None) -> str` (returns the written version name — factored this way so the test can call it directly without subprocessing).

- [ ] **Step 1: Write the failing test**

This is an end-to-end integration test using small synthetic CSVs (not the real Kaggle dataset — that stays a manual step, see Task 18).

```python
# forecasting/tests/test_cli.py
import numpy as np
import pandas as pd
import pytest

from training import artifact, cli


def _schrijf_synthetische_data(tmp_path, n_dagen=140, n_winkels=3):
    rng = np.random.default_rng(7)
    rijen = []
    for store in range(1, n_winkels + 1):
        datums = pd.date_range("2015-01-01", periods=n_dagen, freq="D")
        basis = 800 + store * 100
        for i, datum in enumerate(datums):
            rijen.append({
                "Store": store, "DayOfWeek": datum.dayofweek + 1, "Date": datum.strftime("%Y-%m-%d"),
                "Sales": basis + 50 * np.sin(i / 7) + rng.normal(0, 20),
                "Customers": 100, "Open": 1, "Promo": int(i % 5 == 0),
                "StateHoliday": "0", "SchoolHoliday": 0,
            })
    train_pad = tmp_path / "train.csv"
    pd.DataFrame(rijen).to_csv(train_pad, index=False)

    winkels_pad = tmp_path / "store.csv"
    pd.DataFrame({
        "Store": range(1, n_winkels + 1),
        "StoreType": ["a"] * n_winkels,
        "Assortment": ["a"] * n_winkels,
        "CompetitionDistance": [500.0 * s for s in range(1, n_winkels + 1)],
    }).to_csv(winkels_pad, index=False)

    return train_pad, winkels_pad


def test_cli_end_to_end_schrijft_artefact(tmp_path):
    train_pad, winkels_pad = _schrijf_synthetische_data(tmp_path)
    models_dir = tmp_path / "models"

    versie = cli.main([
        "--train", str(train_pad), "--winkels", str(winkels_pad), "--models-dir", str(models_dir),
    ])

    geladen = artifact.laad_artefact(models_dir, versie)
    assert set(geladen["modellen"].keys()) == {0.1, 0.5, 0.9}
    assert 0.0 <= geladen["metadata"]["metrics"]["rmspe"]
    assert geladen["metadata"]["gevalideerde_horizon_dagen"] == cli.TEST_DAGEN
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd forecasting && pytest tests/test_cli.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'training.cli'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/training/cli.py
"""Command-line entry point: draait de volledige pipeline + training +
evaluatie + artefact-oplevering in één commando.

Gebruik: python3 -m training.cli --train data/train.csv --winkels data/store.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.features import bouw_features
from pipeline.ingest import laad_train, laad_winkels, samenvoegen
from pipeline.split import walk_forward_split
from training.artifact import bewaar_historie, bewaar_winkel_metadata, schrijf_artefact
from training.evaluate import evalueer
from training.train import train_alle_kwantielen

VALIDATIE_DAGEN = 48
TEST_DAGEN = 48


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--winkels", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--encrypt", action="store_true")
    args = parser.parse_args(argv)

    transacties = laad_train(args.train)
    winkels = laad_winkels(args.winkels)
    samengevoegd = samenvoegen(transacties, winkels)
    met_features = bouw_features(samengevoegd)

    train_df, _validatie, test_df = walk_forward_split(met_features, VALIDATIE_DAGEN, TEST_DAGEN)

    modellen = train_alle_kwantielen(train_df)
    metrics = evalueer(modellen, test_df)
    print(f"RMSPE: {metrics['rmspe']:.4f}  coverage p10-p90: {metrics['coverage_p10_p90']:.2%}")

    historie = bewaar_historie(met_features, tot_en_met=train_df["Date"].max())
    winkel_metadata = bewaar_winkel_metadata(winkels)

    versie = schrijf_artefact(
        basis_map=args.models_dir,
        modellen=modellen,
        historie=historie,
        winkel_metadata=winkel_metadata,
        metrics=metrics,
        trainingsperiode=(train_df["Date"].min(), train_df["Date"].max()),
        gevalideerde_horizon_dagen=TEST_DAGEN,
        versleuteld=args.encrypt,
    )
    print(f"Artefact weggeschreven als versie: {versie}")
    print(f"Zet MODEL_VERSION={versie} in .env om deze versie te serveren.")
    return versie


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd forecasting && pytest tests/test_cli.py -v
```

Expected: 1 passed. (Runtime note: this trains 3 real XGBoost models on ~400 rows, should complete in well under a minute.)

- [ ] **Step 5: Commit**

```bash
git add forecasting/training/cli.py forecasting/tests/test_cli.py
git commit -m "forecasting: add end-to-end training CLI"
```

---

## Task 12: Serving configuration with hard-fail (`serving/config.py`)

**Files:**
- Create: `forecasting/serving/config.py`
- Test: `forecasting/tests/test_config.py`

**Interfaces:**
- Produces: `Settings` (frozen dataclass with fields `model_version`, `models_dir`, `api_keys_file`, `audit_log_file`, `cors_allowed_origins: list[str]`, `encrypt_at_rest: bool`, `rate_limit_per_minute: int`), `laad_settings() -> Settings`.

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_config.py
import pytest

from serving import config


def _basis_env(monkeypatch, tmp_path, **overrides):
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")
    env = {
        "MODEL_VERSION": "20260101T000000Z",
        "API_KEYS_FILE": str(tmp_path / "api_keys.json"),
        **overrides,
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)


def test_laad_settings_faalt_hard_zonder_model_version(monkeypatch, tmp_path):
    monkeypatch.delenv("MODEL_VERSION", raising=False)
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    with pytest.raises(RuntimeError, match="MODEL_VERSION"):
        config.laad_settings()


def test_laad_settings_faalt_hard_zonder_api_keys_bestand(monkeypatch, tmp_path):
    monkeypatch.setenv("MODEL_VERSION", "20260101T000000Z")
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "ontbreekt.json"))
    with pytest.raises(RuntimeError, match="API_KEYS_FILE"):
        config.laad_settings()


def test_laad_settings_faalt_hard_bij_encryptie_zonder_sleutel(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path, FORECASTING_ENCRYPT_AT_REST="true")
    monkeypatch.delenv("FORECASTING_ENCRYPTIE_SLEUTEL", raising=False)
    with pytest.raises(RuntimeError, match="FORECASTING_ENCRYPTIE_SLEUTEL"):
        config.laad_settings()


def test_laad_settings_lege_cors_origins_geeft_lege_lijst(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path)
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    settings = config.laad_settings()
    assert settings.cors_allowed_origins == []


def test_laad_settings_parsed_meerdere_cors_origins(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path, CORS_ALLOWED_ORIGINS="https://tessar.nl, https://staging.tessar.nl")
    settings = config.laad_settings()
    assert settings.cors_allowed_origins == ["https://tessar.nl", "https://staging.tessar.nl"]


def test_laad_settings_defaults_toegepast(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path)
    for var in ("MODELS_DIR", "AUDIT_LOG_FILE", "RATE_LIMIT_PER_MINUUT", "FORECASTING_ENCRYPT_AT_REST"):
        monkeypatch.delenv(var, raising=False)
    settings = config.laad_settings()
    assert settings.encrypt_at_rest is False
    assert settings.rate_limit_per_minute == 60
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'serving.config'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/serving/config.py
"""Configuratie voor de serving-laag: leest environment variables, faalt
hard bij ontbrekende verplichte waarden — nooit een stille default voor iets
dat veiligheids- of correctheidskritisch is."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model_version: str
    models_dir: Path
    api_keys_file: Path
    audit_log_file: Path
    cors_allowed_origins: list[str]
    encrypt_at_rest: bool
    rate_limit_per_minute: int


def laad_settings() -> Settings:
    model_version = os.environ.get("MODEL_VERSION")
    if not model_version:
        raise RuntimeError(
            "MODEL_VERSION ontbreekt in de omgeving. Zet 'm expliciet op een "
            "gepromoveerde modelversie (map onder models/) — de server start "
            "nooit met een impliciet 'laatste' model."
        )

    models_dir = Path(os.environ.get("MODELS_DIR", "models"))

    api_keys_file = Path(os.environ.get("API_KEYS_FILE", "api_keys.json"))
    if not api_keys_file.exists():
        raise RuntimeError(
            f"API_KEYS_FILE ({api_keys_file}) bestaat niet. Voeg minimaal één "
            "key toe met security.api_keys.voeg_key_toe() voordat de server start."
        )

    audit_log_file = Path(os.environ.get("AUDIT_LOG_FILE", "audit.log"))

    ruwe_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    cors_allowed_origins = [o.strip() for o in ruwe_origins.split(",") if o.strip()]
    # Ontbrekende/lege config = expliciet geen enkele origin toegestaan.
    # Nooit een wildcard-fallback, ook niet impliciet.

    encrypt_at_rest = os.environ.get("FORECASTING_ENCRYPT_AT_REST", "false").lower() == "true"
    if encrypt_at_rest and not os.environ.get("FORECASTING_ENCRYPTIE_SLEUTEL"):
        raise RuntimeError(
            "FORECASTING_ENCRYPT_AT_REST staat aan, maar FORECASTING_ENCRYPTIE_SLEUTEL "
            "ontbreekt. Genereer een sleutel met: python3 -m security.encryptie genereer-sleutel"
        )

    rate_limit = int(os.environ.get("RATE_LIMIT_PER_MINUUT", "60"))

    return Settings(
        model_version=model_version,
        models_dir=models_dir,
        api_keys_file=api_keys_file,
        audit_log_file=audit_log_file,
        cors_allowed_origins=cors_allowed_origins,
        encrypt_at_rest=encrypt_at_rest,
        rate_limit_per_minute=rate_limit,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_config.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/serving/config.py forecasting/tests/test_config.py
git commit -m "forecasting: add hard-failing serving configuration"
```

---

## Task 13: Request/response schemas (`serving/schemas.py`)

**Files:**
- Create: `forecasting/serving/schemas.py`
- Test: `forecasting/tests/test_schemas.py`

**Interfaces:**
- Produces: `ForecastVerzoek(store_id: int, start_datum: date, horizon_dagen: int)`, `DagVoorspelling(datum: date, p10: float, p50: float, p90: float)`, `ForecastResponse(store_id: int, voorspellingen: list[DagVoorspelling])`, `MetricsResponse(model_versie: str, rmspe: float, coverage_p10_p90: float, n_observaties: int, gevalideerde_horizon_dagen: int)`.

Note: the actual horizon-vs-validated-window business rule needs the loaded model's metadata, which isn't known at schema-definition time — that check lives in Task 15's endpoint handler, not here. This schema only enforces structural sanity (positive values).

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_schemas.py
import pytest
from pydantic import ValidationError

from serving.schemas import DagVoorspelling, ForecastResponse, ForecastVerzoek, MetricsResponse


def test_forecast_verzoek_accepteert_geldige_input():
    verzoek = ForecastVerzoek(store_id=1, start_datum="2015-08-01", horizon_dagen=14)
    assert verzoek.store_id == 1
    assert verzoek.horizon_dagen == 14


def test_forecast_verzoek_verwerpt_negatief_store_id():
    with pytest.raises(ValidationError):
        ForecastVerzoek(store_id=-1, start_datum="2015-08-01", horizon_dagen=14)


def test_forecast_verzoek_verwerpt_nul_horizon():
    with pytest.raises(ValidationError):
        ForecastVerzoek(store_id=1, start_datum="2015-08-01", horizon_dagen=0)


def test_forecast_response_serialiseert():
    response = ForecastResponse(
        store_id=1,
        voorspellingen=[DagVoorspelling(datum="2015-08-01", p10=100.0, p50=150.0, p90=200.0)],
    )
    data = response.model_dump(mode="json")
    assert data["voorspellingen"][0]["p50"] == 150.0


def test_metrics_response_serialiseert():
    response = MetricsResponse(
        model_versie="20260101T000000Z", rmspe=0.12, coverage_p10_p90=0.81,
        n_observaties=1000, gevalideerde_horizon_dagen=48,
    )
    assert response.model_dump()["rmspe"] == 0.12
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_schemas.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'serving.schemas'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/serving/schemas.py
"""Pydantic-schema's voor de forecasting-API. De horizon-vs-gevalideerde-
periode-controle staat bewust niet hier — die vereist het geladen
modelartefact, dat pas bij de endpoint-handler bekend is (zie serving/app.py)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ForecastVerzoek(BaseModel):
    store_id: int = Field(..., gt=0)
    start_datum: date
    horizon_dagen: int = Field(..., gt=0)


class DagVoorspelling(BaseModel):
    datum: date
    p10: float
    p50: float
    p90: float


class ForecastResponse(BaseModel):
    store_id: int
    voorspellingen: list[DagVoorspelling]


class MetricsResponse(BaseModel):
    model_versie: str
    rmspe: float
    coverage_p10_p90: float
    n_observaties: int
    gevalideerde_horizon_dagen: int
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_schemas.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/serving/schemas.py forecasting/tests/test_schemas.py
git commit -m "forecasting: add API request/response schemas"
```

---

## Task 14: Recursive forecasting (`serving/forecast.py`)

This is the piece that reconstructs features at request time from the bundled history, and predicts multi-day horizons recursively (feeding each day's p50 back in as the working value for the next day's lag features) — because the shortest lag (7 days) is smaller than the validated horizon (48 days), direct reconstruction from real actuals alone isn't possible past day 7. This is a deliberate design choice with a known, documented limitation (compounding error over longer horizons — see Task 19).

**Files:**
- Create: `forecasting/serving/forecast.py`
- Test: `forecasting/tests/test_forecast.py`

**Interfaces:**
- Consumes: `pipeline.features.voeg_kalenderfeatures_toe`, `voeg_lag_features_toe` (Task 6), `training.train.FEATURE_KOLOMMEN` (Task 8), `training.evaluate.sorteer_kwantielen` (Task 9).
- Produces: `OnbekendeWinkel(Exception)`, `HorizonBuitenBereik(Exception)`, `voorspel_periode(modellen, historie, winkel_metadata, store_id, start_datum, horizon_dagen) -> pd.DataFrame` with columns `Date, p10, p50, p90`.

- [ ] **Step 1: Write the failing tests**

```python
# forecasting/tests/test_forecast.py
import numpy as np
import pandas as pd
import pytest

from serving.forecast import HorizonBuitenBereik, OnbekendeWinkel, voorspel_periode


class _NepModel:
    """Voorspelt altijd de rolling_gemiddeld_7-feature terug, zodat de test
    kan verifiëren dat features daadwerkelijk worden aangeleverd."""
    def predict(self, X):
        return X["omzet_rolling_gemiddeld_7"].to_numpy()


def _historie(store_id=1, n_dagen=40, basis=1000.0):
    datums = pd.date_range("2015-06-01", periods=n_dagen, freq="D")
    return pd.DataFrame({
        "Store": store_id, "Date": datums,
        "Sales": [basis + i for i in range(n_dagen)], "Open": 1,
    })


def _winkel_metadata(store_id=1):
    return pd.DataFrame({"Store": [store_id], "CompetitionDistance": [500.0]})


def test_voorspel_periode_onbekende_winkel_raiset():
    with pytest.raises(OnbekendeWinkel):
        voorspel_periode(
            modellen={q: _NepModel() for q in (0.1, 0.5, 0.9)},
            historie=_historie(), winkel_metadata=_winkel_metadata(),
            store_id=999, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=3,
        )


def test_voorspel_periode_geeft_juiste_aantal_dagen():
    resultaat = voorspel_periode(
        modellen={q: _NepModel() for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        store_id=1, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=5,
    )
    assert len(resultaat) == 5
    assert list(resultaat.columns) == ["Date", "p10", "p50", "p90"]


def test_voorspel_periode_sorteert_gekruiste_kwantielen():
    class _GekruistModel:
        def __init__(self, waarde):
            self.waarde = waarde
        def predict(self, X):
            return np.full(len(X), self.waarde)

    # p10-model geeft een HOGERE waarde dan het p90-model -> moet gesorteerd worden
    modellen = {0.1: _GekruistModel(500.0), 0.5: _GekruistModel(300.0), 0.9: _GekruistModel(100.0)}
    resultaat = voorspel_periode(
        modellen=modellen, historie=_historie(), winkel_metadata=_winkel_metadata(),
        store_id=1, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=1,
    )
    rij = resultaat.iloc[0]
    assert rij["p10"] <= rij["p50"] <= rij["p90"]


def test_voorspel_periode_onvoldoende_historie_raiset():
    korte_historie = _historie(n_dagen=3)  # te weinig voor lag_7/lag_14/lag_21
    with pytest.raises(HorizonBuitenBereik):
        voorspel_periode(
            modellen={q: _NepModel() for q in (0.1, 0.5, 0.9)},
            historie=korte_historie, winkel_metadata=_winkel_metadata(),
            store_id=1, start_datum=pd.Timestamp("2015-06-05"), horizon_dagen=1,
        )


def test_voorspel_periode_werkt_voorbij_de_kortste_lag():
    # horizon_dagen=10 > lag_7 (7 dagen) -> vereist de recursieve stap
    resultaat = voorspel_periode(
        modellen={q: _NepModel() for q in (0.1, 0.5, 0.9)},
        historie=_historie(n_dagen=40), winkel_metadata=_winkel_metadata(),
        store_id=1, start_datum=pd.Timestamp("2015-07-11"), horizon_dagen=10,
    )
    assert len(resultaat) == 10
    assert resultaat["p50"].notna().all()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_forecast.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'serving.forecast'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/serving/forecast.py
"""Voorspellingslogica: reconstrueert features uit de gebundelde historie en
roept de drie kwantielmodellen aan.

Voorspelt recursief: elke volgende dag gebruikt de p50-voorspelling van
eerder voorspelde dagen als werkwaarde voor de lag-/rolling-features. Dit is
nodig omdat de gevalideerde horizon (tot 48 dagen) de langste lag (21 dagen)
kan overschrijden — de werkelijke omzet van een nog niet aangebroken dag is
per definitie onbekend. Compounding van fouten over een langere horizon is
een bekende, geaccepteerde beperking van deze aanpak (zie
KNOWN-LIMITATIONS.md). Hergebruikt dezelfde featurefuncties als tijdens
training, zodat serving-tijd-features nooit op een subtiel andere manier
worden berekend dan trainings-tijd-features."""
from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline.features import voeg_kalenderfeatures_toe, voeg_lag_features_toe
from training.evaluate import sorteer_kwantielen
from training.train import FEATURE_KOLOMMEN


class OnbekendeWinkel(Exception):
    pass


class HorizonBuitenBereik(Exception):
    pass


def voorspel_periode(
    modellen: dict[float, object],
    historie: pd.DataFrame,
    winkel_metadata: pd.DataFrame,
    store_id: int,
    start_datum: pd.Timestamp,
    horizon_dagen: int,
) -> pd.DataFrame:
    if store_id not in historie["Store"].unique():
        raise OnbekendeWinkel(f"Onbekend store_id: {store_id}")

    start_datum = pd.Timestamp(start_datum)
    werkreeks = historie[historie["Store"] == store_id][["Store", "Date", "Sales", "Open"]].copy()
    resultaten = []

    for i in range(horizon_dagen):
        doel_datum = start_datum + pd.Timedelta(days=i)
        nieuwe_rij = pd.DataFrame({"Store": [store_id], "Date": [doel_datum], "Sales": [np.nan], "Open": [1]})
        volledig = pd.concat([werkreeks, nieuwe_rij], ignore_index=True)
        volledig = voeg_kalenderfeatures_toe(volledig)
        volledig = voeg_lag_features_toe(volledig)
        volledig = volledig.merge(winkel_metadata, on="Store", how="left")

        feature_rij = volledig.iloc[[-1]]
        if feature_rij[FEATURE_KOLOMMEN].isna().any(axis=1).iloc[0]:
            raise HorizonBuitenBereik(
                f"Onvoldoende historie om {doel_datum.date()} te voorspellen voor winkel {store_id}."
            )

        ruwe = {q: float(modellen[q].predict(feature_rij[FEATURE_KOLOMMEN])[0]) for q in (0.1, 0.5, 0.9)}
        p10, p50, p90 = sorteer_kwantielen(
            np.array([ruwe[0.1]]), np.array([ruwe[0.5]]), np.array([ruwe[0.9]])
        )
        resultaten.append({"Date": doel_datum, "p10": float(p10[0]), "p50": float(p50[0]), "p90": float(p90[0])})

        werkreeks = pd.concat(
            [werkreeks, pd.DataFrame({"Store": [store_id], "Date": [doel_datum], "Sales": [float(p50[0])], "Open": [1]})],
            ignore_index=True,
        )

    return pd.DataFrame(resultaten)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_forecast.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/serving/forecast.py forecasting/tests/test_forecast.py
git commit -m "forecasting: add recursive multi-day forecasting with feature parity to training"
```

---

## Task 15: FastAPI app (`serving/app.py`)

**Files:**
- Create: `forecasting/serving/app.py`
- Test: `forecasting/tests/test_app.py`

**Interfaces:**
- Consumes: `serving.config.laad_settings` (Task 12), `serving.schemas.*` (Task 13), `serving.forecast.voorspel_periode` (Task 14), `training.artifact.laad_artefact` (Task 10), `security.api_keys.vind_key_naam` (Task 3), `security.audit.log` (Task 4).
- Produces: FastAPI `app` object with routes `GET /health`, `POST /forecast`, `GET /metrics`, plus a static mount at `/` for `dashboard/`.

- [ ] **Step 1: Write the failing tests**

The app reads config and loads a model artifact at import time, so the tests build a real tiny artifact in a `tmp_path` and point the app at it via environment variables before importing.

```python
# forecasting/tests/test_app.py
import importlib
import sys

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from security import api_keys
from training import artifact, train


def _bouw_test_omgeving(tmp_path, monkeypatch, cors_origins=""):
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

    keys_pad = tmp_path / "api_keys.json"
    api_keys.voeg_key_toe(keys_pad, "test-klant", "test-key-123")

    monkeypatch.setenv("MODEL_VERSION", versie)
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(keys_pad))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", cors_origins)
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", "1000")

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return TestClient(module.app)


def test_health_werkt_zonder_auth(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_forecast_zonder_key_geeft_401(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.post("/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3})
    assert resp.status_code == 401


def test_forecast_met_ongeldige_key_geeft_401(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "fout"},
    )
    assert resp.status_code == 401


def test_forecast_met_geldige_key_geeft_voorspellingen(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "test-key-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["voorspellingen"]) == 3
    for dag in data["voorspellingen"]:
        assert dag["p10"] <= dag["p50"] <= dag["p90"]


def test_forecast_onbekende_winkel_geeft_404(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.post(
        "/forecast", json={"store_id": 999, "start_datum": "2015-07-11", "horizon_dagen": 3},
        headers={"X-API-Key": "test-key-123"},
    )
    assert resp.status_code == 404


def test_forecast_horizon_boven_gevalideerde_periode_geeft_422(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 9999},
        headers={"X-API-Key": "test-key-123"},
    )
    assert resp.status_code == 422


def test_metrics_geeft_gevalideerde_cijfers(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.get("/metrics", headers={"X-API-Key": "test-key-123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["rmspe"] == 0.15
    assert data["coverage_p10_p90"] == 0.79


def test_cors_ontbrekende_config_staat_geen_enkele_origin_toe(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch, cors_origins="")
    resp = client.get(
        "/health", headers={"Origin": "https://willekeurige-site.example"},
    )
    assert "access-control-allow-origin" not in resp.headers


def test_cors_toegestane_origin_krijgt_header(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch, cors_origins="https://tessar.nl")
    resp = client.get("/health", headers={"Origin": "https://tessar.nl"})
    assert resp.headers.get("access-control-allow-origin") == "https://tessar.nl"


def test_audit_log_bevat_verzoek_metadata(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    client.post(
        "/forecast", json={"store_id": 1, "start_datum": "2015-07-11", "horizon_dagen": 2},
        headers={"X-API-Key": "test-key-123"},
    )
    import json
    regel = json.loads((tmp_path / "audit.log").read_text(encoding="utf-8").strip().splitlines()[0])
    assert regel["key"] == "test-klant"
    assert regel["statuscode"] == 200
    assert "store_id" in regel
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd forecasting && pytest tests/test_app.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'serving.app'`.

- [ ] **Step 3: Write the implementation**

```python
# forecasting/serving/app.py
"""FastAPI-app: dunne serving-laag, traint nooit zelf. Laadt bij import een
expliciet gepinde modelversie (MODEL_VERSION) — hard-fail als die ontbreekt
of niet bestaat, nooit een impliciet 'laatste' model."""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from security import api_keys, audit
from serving.config import laad_settings
from serving.forecast import HorizonBuitenBereik, OnbekendeWinkel, voorspel_periode
from serving.schemas import DagVoorspelling, ForecastResponse, ForecastVerzoek, MetricsResponse
from training.artifact import laad_artefact

settings = laad_settings()
artefact = laad_artefact(settings.models_dir, settings.model_version, versleuteld=settings.encrypt_at_rest)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])

app = FastAPI(title="Tessar Vraagvoorspelling")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def vereis_api_key(sleutel: str | None = Security(api_key_header)) -> str:
    if not sleutel:
        raise HTTPException(status_code=401, detail="X-API-Key header ontbreekt.")
    naam = api_keys.vind_key_naam(settings.api_keys_file, sleutel)
    if naam is None:
        raise HTTPException(status_code=401, detail="Ongeldige API-key.")
    return naam


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_versie": settings.model_version}


@app.post("/forecast", response_model=ForecastResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def forecast(
    request: Request, verzoek: ForecastVerzoek, key_naam: str = Depends(vereis_api_key)
) -> ForecastResponse:
    gevalideerde_horizon = artefact["metadata"]["gevalideerde_horizon_dagen"]
    if verzoek.horizon_dagen > gevalideerde_horizon:
        raise HTTPException(
            status_code=422,
            detail=(
                f"horizon_dagen ({verzoek.horizon_dagen}) overschrijdt de tijdens training "
                f"gevalideerde periode ({gevalideerde_horizon} dagen)."
            ),
        )

    start = time.monotonic()
    statuscode = 500
    try:
        resultaat = voorspel_periode(
            modellen=artefact["modellen"],
            historie=artefact["historie"],
            winkel_metadata=artefact["winkel_metadata"],
            store_id=verzoek.store_id,
            start_datum=verzoek.start_datum,
            horizon_dagen=verzoek.horizon_dagen,
        )
        statuscode = 200
    except OnbekendeWinkel:
        statuscode = 404
        raise HTTPException(status_code=404, detail=f"Onbekend store_id: {verzoek.store_id}")
    except HorizonBuitenBereik as e:
        statuscode = 422
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        audit.log(
            settings.audit_log_file,
            {
                "key": key_naam,
                "store_id": verzoek.store_id,
                "horizon_dagen": verzoek.horizon_dagen,
                "statuscode": statuscode,
                "latency_ms": round((time.monotonic() - start) * 1000, 1),
            },
            versleuteld=settings.encrypt_at_rest,
        )

    return ForecastResponse(
        store_id=verzoek.store_id,
        voorspellingen=[
            DagVoorspelling(datum=rij["Date"].date(), p10=rij["p10"], p50=rij["p50"], p90=rij["p90"])
            for _, rij in resultaat.iterrows()
        ],
    )


@app.get("/metrics", response_model=MetricsResponse)
def metrics(key_naam: str = Depends(vereis_api_key)) -> MetricsResponse:
    m = artefact["metadata"]
    return MetricsResponse(
        model_versie=m["versie"],
        rmspe=m["metrics"]["rmspe"],
        coverage_p10_p90=m["metrics"]["coverage_p10_p90"],
        n_observaties=m["metrics"]["n_observaties"],
        gevalideerde_horizon_dagen=m["gevalideerde_horizon_dagen"],
    )


_dashboard_pad = Path(__file__).resolve().parent.parent / "dashboard"
if _dashboard_pad.exists():
    app.mount("/", StaticFiles(directory=str(_dashboard_pad), html=True), name="dashboard")
```

Note: the static mount is guarded with `if _dashboard_pad.exists()` because Task 15 runs before Task 16 creates `dashboard/` — without the guard, `StaticFiles` raises at import time and every test in this task would fail before the dashboard exists. Task 16 will not need to touch this file.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd forecasting && pytest tests/test_app.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add forecasting/serving/app.py forecasting/tests/test_app.py
git commit -m "forecasting: add FastAPI serving layer (auth, CORS, rate limiting, audit)"
```

---

## Task 16: Dashboard (static frontend)

**Files:**
- Create: `forecasting/dashboard/index.html`
- Create: `forecasting/dashboard/dashboard.js`

**Interfaces:**
- Consumes: `GET /metrics`, `POST /forecast` (Task 15) via a configurable base URL (`window.TESSAR_FORECAST_API_BASIS`, defaults to `/api` — see note below on the local dev proxy path).
- Produces: a browser-viewable page with a store selector, date/horizon inputs, an SVG chart (p10–p90 band + p50 line, no external chart library — consistent with the rest of the Tessar site, which has none), and the live RMSPE/coverage numbers.

No automated test for this task (it's a static page); verification is manual in Step 3.

- [ ] **Step 1: Write `forecasting/dashboard/index.html`**

```html
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Vraagvoorspelling — demo</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  html, body { margin:0; padding:0; background:oklch(98% 0.004 90); font-family:'IBM Plex Sans', -apple-system, sans-serif; color:oklch(18% 0.02 255); }
  .wrap { max-width:1000px; margin:0 auto; padding:clamp(20px,5vw,40px); }
  h1 { font:700 clamp(1.5rem,3vw,2rem)/1.3 'IBM Plex Sans'; margin:0 0 8px; }
  .sub { color:oklch(46% 0.012 140); margin:0 0 28px; }
  .controls { display:flex; gap:16px; align-items:end; flex-wrap:wrap; margin-bottom:24px; }
  label { display:block; font:600 0.8125rem/1.4 'IBM Plex Sans'; margin-bottom:6px; }
  select, input, button { font:400 0.9375rem/1.4 'IBM Plex Sans'; padding:8px 12px; border:1px solid oklch(85% 0.006 90); border-radius:6px; background:#fff; }
  button { background:oklch(70% 0.14 220); color:#001a2e; font-weight:700; border:none; cursor:pointer; }
  button:disabled { opacity:0.5; cursor:not-allowed; }
  .metrics { display:flex; gap:24px; margin-bottom:24px; flex-wrap:wrap; }
  .metric { border:1px solid oklch(91% 0.006 90); border-radius:10px; padding:14px 18px; background:#fff; }
  .metric .label { font:600 0.75rem/1.2 'IBM Plex Mono'; text-transform:uppercase; letter-spacing:0.05em; color:oklch(46% 0.012 140); }
  .metric .value { font:700 1.375rem/1.3 'IBM Plex Sans'; color:oklch(18% 0.02 255); }
  #chart-container { border:1px solid oklch(91% 0.006 90); border-radius:12px; background:#fff; padding:20px; overflow-x:auto; }
  .band { fill:oklch(70% 0.14 220 / 0.15); }
  .lijn { fill:none; stroke:oklch(48% 0.12 230); stroke-width:2; }
  .as { stroke:oklch(85% 0.006 90); stroke-width:1; }
  .fout { color:oklch(50% 0.18 25); margin-top:12px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Vraagvoorspelling — demo</h1>
  <p class="sub">Voorbeeld op basis van een model getraind en gevalideerd op historische retaildata.</p>

  <div class="controls">
    <div>
      <label for="store">Winkel-ID</label>
      <select id="store"></select>
    </div>
    <div>
      <label for="start">Startdatum</label>
      <input type="date" id="start">
    </div>
    <div>
      <label for="horizon">Horizon (dagen)</label>
      <input type="number" id="horizon" value="14" min="1">
    </div>
    <div>
      <button id="voorspel">Voorspel</button>
    </div>
  </div>

  <div class="metrics" id="metrics"></div>
  <div id="chart-container"><svg id="chart" width="920" height="360"></svg></div>
  <p class="fout" id="fout" hidden></p>
</div>

<script src="./dashboard.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `forecasting/dashboard/dashboard.js`**

```javascript
"use strict";

// Configureerbaar API-adres: lokaal same-origin (de FastAPI-app serveert dit
// dashboard zelf onder dezelfde origin), later het live adres van de
// forecasting-API zodra dit dashboard op de Tessar-website staat — dan wordt
// TESSAR_FORECAST_API_BASIS vóór het laden van dit script gezet.
const API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";
const API_KEY = window.TESSAR_FORECAST_API_KEY || "";

const WINKEL_IDS = [1, 2, 3, 4, 5, 10, 25, 50, 100, 250];

function vulWinkelSelect() {
  const select = document.getElementById("store");
  for (const id of WINKEL_IDS) {
    const optie = document.createElement("option");
    optie.value = String(id);
    optie.textContent = `Winkel ${id}`;
    select.appendChild(optie);
  }
}

function toonFout(bericht) {
  const el = document.getElementById("fout");
  el.textContent = bericht;
  el.hidden = !bericht;
}

async function laadMetrics() {
  const resp = await fetch(`${API_BASIS}/metrics`, { headers: { "X-API-Key": API_KEY } });
  if (!resp.ok) throw new Error(`Kon nauwkeurigheidscijfers niet ophalen (${resp.status})`);
  const data = await resp.json();
  const container = document.getElementById("metrics");
  container.innerHTML = "";
  const items = [
    ["RMSPE", (data.rmspe * 100).toFixed(1) + "%"],
    ["Dekking p10–p90-band", (data.coverage_p10_p90 * 100).toFixed(0) + "%"],
    ["Modelversie", data.model_versie],
  ];
  for (const [label, waarde] of items) {
    const kaart = document.createElement("div");
    kaart.className = "metric";
    kaart.innerHTML = `<div class="label">${label}</div><div class="value">${waarde}</div>`;
    container.appendChild(kaart);
  }
  return data;
}

async function haalVoorspelling(storeId, startDatum, horizonDagen) {
  const resp = await fetch(`${API_BASIS}/forecast`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify({ store_id: storeId, start_datum: startDatum, horizon_dagen: horizonDagen }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Voorspelling mislukt (${resp.status})`);
  }
  return resp.json();
}

function tekenGrafiek(voorspellingen) {
  const svg = document.getElementById("chart");
  const breedte = 920, hoogte = 360, marge = { boven: 20, rechts: 20, onder: 30, links: 50 };
  const plotBreedte = breedte - marge.links - marge.rechts;
  const plotHoogte = hoogte - marge.boven - marge.onder;

  const alleWaarden = voorspellingen.flatMap((v) => [v.p10, v.p90]);
  const minY = Math.min(...alleWaarden) * 0.95;
  const maxY = Math.max(...alleWaarden) * 1.05;

  const x = (i) => marge.links + (i / (voorspellingen.length - 1 || 1)) * plotBreedte;
  const y = (waarde) => marge.boven + plotHoogte - ((waarde - minY) / (maxY - minY)) * plotHoogte;

  const bandPunten = [
    ...voorspellingen.map((v, i) => `${x(i)},${y(v.p90)}`),
    ...[...voorspellingen].reverse().map((v, i) => `${x(voorspellingen.length - 1 - i)},${y(v.p10)}`),
  ].join(" ");
  const lijnPunten = voorspellingen.map((v, i) => `${x(i)},${y(v.p50)}`).join(" ");

  svg.innerHTML = `
    <polygon class="band" points="${bandPunten}"></polygon>
    <polyline class="lijn" points="${lijnPunten}"></polyline>
    <line class="as" x1="${marge.links}" y1="${marge.boven}" x2="${marge.links}" y2="${hoogte - marge.onder}"></line>
    <line class="as" x1="${marge.links}" y1="${hoogte - marge.onder}" x2="${breedte - marge.rechts}" y2="${hoogte - marge.onder}"></line>
  `;
}

async function voorspel() {
  const knop = document.getElementById("voorspel");
  knop.disabled = true;
  toonFout("");
  try {
    const storeId = Number(document.getElementById("store").value);
    const startDatum = document.getElementById("start").value;
    const horizonDagen = Number(document.getElementById("horizon").value);
    const data = await haalVoorspelling(storeId, startDatum, horizonDagen);
    tekenGrafiek(data.voorspellingen);
  } catch (e) {
    toonFout(e.message);
  } finally {
    knop.disabled = false;
  }
}

function vandaagPlusEen() {
  const morgen = new Date();
  morgen.setDate(morgen.getDate() + 1);
  return morgen.toISOString().slice(0, 10);
}

document.addEventListener("DOMContentLoaded", () => {
  vulWinkelSelect();
  document.getElementById("start").value = vandaagPlusEen();
  document.getElementById("voorspel").addEventListener("click", voorspel);
  laadMetrics().catch((e) => toonFout(e.message));
});
```

- [ ] **Step 3: Manual verification**

```bash
cd forecasting
source .venv/bin/activate
# Requires a trained artifact and API key from Tasks 11/15 — see Task 20 for
# the full end-to-end smoke test. Once MODEL_VERSION/API_KEYS_FILE are set:
uvicorn serving.app:app --reload
```

Open `http://127.0.0.1:8000/` in a browser. Expected: the page loads with Tessar-style fonts/colors, the metrics cards populate (confirms `/metrics` call succeeds), and clicking "Voorspel" after picking a store draws a shaded band + line in the SVG (confirms `/forecast` call succeeds). Note: since `API_KEY` defaults to empty in the JS, you'll need to either set `window.TESSAR_FORECAST_API_KEY` via the browser console before the fetch calls fire, or temporarily hardcode a valid test key while verifying manually — do not commit a hardcoded key.

- [ ] **Step 4: Commit**

```bash
git add forecasting/dashboard/index.html forecasting/dashboard/dashboard.js
git commit -m "forecasting: add Tessar-styled static dashboard (SVG chart, no external deps)"
```

---

## Task 17: Docker Compose deployment

**Files:**
- Create: `forecasting/Dockerfile`
- Create: `forecasting/docker-compose.yml`

**Interfaces:**
- Consumes: everything from Tasks 1–16.
- Produces: a locally runnable `api` service and a one-off `training` service, per the spec's "lokaal voor nu" deployment decision.

- [ ] **Step 1: Write `forecasting/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY security/ ./security/
COPY pipeline/ ./pipeline/
COPY training/ ./training/
COPY serving/ ./serving/
COPY dashboard/ ./dashboard/

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write `forecasting/docker-compose.yml`**

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./models:/app/models
      - ./api_keys.json:/app/api_keys.json
      - ./audit.log:/app/audit.log
    restart: unless-stopped

  training:
    build: .
    profiles: ["training"]
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./models:/app/models
    entrypoint: ["python3", "-m", "training.cli"]
```

- [ ] **Step 3: Verify the image builds**

```bash
cd forecasting
docker compose build api
```

Expected: build succeeds with no errors. (Does not require `.env`/model artifacts to exist yet — build-only check.)

- [ ] **Step 4: Commit**

```bash
git add forecasting/Dockerfile forecasting/docker-compose.yml
git commit -m "forecasting: add local Docker Compose deployment"
```

---

## Task 18: README (dataset acquisition, license check, usage)

**Files:**
- Create: `forecasting/README.md`

- [ ] **Step 1: Write `forecasting/README.md`**

```markdown
# Tessar — vraagvoorspelling-toolkit

Herbruikbare toolkit voor dienst 02 (Voorspellende modellen & besluitondersteuning):
pipeline, training, een dunne serving-API, en een dashboard. Zie
`docs/superpowers/specs/2026-07-25-vraagvoorspelling-toolkit-design.md` in de
repo-root voor het volledige ontwerp.

## 1. Dataset ophalen (handmatige stap, vóór elke training)

Deze toolkit is gebouwd en gevalideerd op de Rossmann Store Sales-dataset
(Kaggle-competitie). Twee dingen moet je zelf controleren vóórdat je traint:

1. **Toegang.** Downloaden vereist een Kaggle-account + API-token
   (`~/.kaggle/kaggle.json`). Zonder account: gebruik voorlopig een
   synthetische dataset met vergelijkbare structuur (winkels, promoties,
   feestdagen, seizoenspatroon) — dezelfde `training.cli`-flow werkt daar
   ook mee, zie `tests/test_cli.py` voor een voorbeeld van hoe zo'n dataset
   eruitziet.
2. **Licentie.** Lees de competitieregels op de Kaggle-pagina van Rossmann
   Store Sales vóórdat je deze dataset (of afgeleide statistieken ervan)
   ergens buiten dit lokale project gebruikt. Deze toolkit gebruikt Rossmann
   uitsluitend om de methode te bouwen/valideren — er wordt geen ruwe data
   herpubliceerd. Voor een latere publieke website-demo: gebruik
   geanonimiseerde/herschaalde of gekalibreerde synthetische waarden, nooit
   de ruwe Rossmann-cijfers.

Download `train.csv` en `store.csv` naar `data/`.

## 2. Trainen

```bash
source .venv/bin/activate
python3 -m training.cli --train data/train.csv --winkels data/store.csv
```

Dit print de RMSPE en coverage, en schrijft een geversieerd artefact naar
`models/<versie>/`. Zet die versie in `.env`:

```
MODEL_VERSION=<versie uit de output>
```

Voeg minimaal één API-key toe voordat je de server start:

```bash
python3 -c "from pathlib import Path; from security import api_keys; api_keys.voeg_key_toe(Path('api_keys.json'), 'lokaal-testen', 'kies-een-eigen-key')"
```

## 3. Lokaal draaien

```bash
docker compose up api
```

Dashboard: `http://localhost:8000/`. API: `http://localhost:8000/forecast`,
`http://localhost:8000/metrics` (beide vereisen de `X-API-Key`-header).

Hertrainen zonder rebuild:

```bash
docker compose run --rm training --train data/train.csv --winkels data/store.csv
```

(Dit schrijft een nieuwe versie naar `models/`; `MODEL_VERSION` in `.env`
bewust handmatig bijwerken en `api` herstarten om 'm te promoveren — geen
automatische overname van de nieuwste versie.)

## 4. Tests

```bash
pytest -v
```

## 5. Bekende risico's / terugvalopties

- **XGBoost-versie:** kwantiel-regressie (`reg:quantileerror`) vereist
  XGBoost ≥2.0. Als de buildomgeving een oudere versie oplevert: vervang
  `objective="reg:quantileerror"` / `quantile_alpha` in `training/train.py`
  door LightGBM (`objective="quantile"`, `alpha=<kwantiel>`) — dezelfde
  interface (`dict[float, model]` met `.predict()`) blijft dan intact voor
  de rest van de codebase.
- Overige bekende beperkingen: zie `KNOWN-LIMITATIONS.md`.
```

- [ ] **Step 2: Commit**

```bash
git add forecasting/README.md
git commit -m "forecasting: add README with dataset acquisition and usage instructions"
```

---

## Task 19: Known limitations

**Files:**
- Create: `forecasting/KNOWN-LIMITATIONS.md`

- [ ] **Step 1: Write `forecasting/KNOWN-LIMITATIONS.md`**

```markdown
# Bekende beperkingen

Eerlijke documentatie van wat deze toolkit (nog) niet oplost — zelfde
patroon als Certo's `KNOWN-LIMITATIONS.md`.

- **Geen live historiefeed.** De serving-laag reconstrueert lag-/
  rolling-features uit een historiebundel die bij training is vastgelegd,
  niet uit een live-bijgewerkte databron. Voor een echt, lopend
  klantproject moet dit een live feed worden (extern datawarehouse, CRM,
  of periodieke re-training) — niet gebouwd in deze fase.
- **Recursieve meerdaagse voorspelling.** Voor horizons voorbij de kortste
  lag (7 dagen) gebruikt de voorspelling zijn eigen eerdere p50-uitkomsten
  als werkwaarde voor latere lag-features. Fouten kunnen zich opstapelen
  over een langere horizon — dit is inherent aan de recursieve aanpak, niet
  een bug.
- **Rate limiting is per-instance.** De in-memory rate limiter houdt geen
  gedeelde staat bij tussen meerdere gelijktijdige API-instances. Geldig
  voor deze fase (één instance), niet voor een horizontaal geschaalde
  deployment.
- **Dataset-licentie.** Rossmann Store Sales is een Kaggle-competitiedataset
  met eigen gebruiksvoorwaarden — geverifieerd tijdens implementatie, zie
  README.md sectie 1. Deze toolkit toont er nooit ruwe cijfers uit op een
  publiek kanaal; alleen afgeleide, gevalideerde nauwkeurigheidscijfers.
- **Geen CI-pipeline.** `pip-audit` en de testsuite zijn handmatige
  controles vóór oplevering, geen geautomatiseerde build-gate — die bestaat
  in deze fase niet.
- **Geen live deployment.** Draait lokaal via Docker Compose. Live
  deployment (bv. naast Certo, met een Caddy-reverse-proxy) en de
  daadwerkelijke website-demo-integratie zijn bewuste, losse
  vervolgstappen.
```

- [ ] **Step 2: Commit**

```bash
git add forecasting/KNOWN-LIMITATIONS.md
git commit -m "forecasting: document known limitations"
```

---

## Task 20: Final verification

**Files:** none created — this task runs checks across everything built in Tasks 1–19.

- [ ] **Step 1: Run the full test suite**

```bash
cd forecasting && source .venv/bin/activate && pytest -v
```

Expected: all tests from Tasks 2–15 pass (encryptie, api_keys, audit, ingest, features, split, train, evaluate, artifact, cli, config, schemas, forecast, app — roughly 70 tests total). If any fail, fix before continuing — do not proceed to a manual smoke test on top of a red suite.

- [ ] **Step 2: Run `pip-audit`**

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

Expected: no known vulnerabilities, or a documented decision (in `KNOWN-LIMITATIONS.md`) for any that can't be immediately resolved.

- [ ] **Step 3: Manually verify the leakage boundary on the actual trained artifact**

After running the real training CLI against the downloaded Rossmann data (Task 18, section 1–2):

```bash
python3 -c "
import json
from pathlib import Path
meta = json.loads((Path('models') / '<versie>' / 'metadata.json').read_text())
print(meta['trainingsperiode_start'], '->', meta['trainingsperiode_eind'])
print(meta['metrics'])
"
```

Confirm the training period end date is well before the known Rossmann test window (2015-08-01 onward), and that `rmspe`/`coverage_p10_p90` are in a plausible range (RMSPE typically 0.10–0.20 for this dataset; coverage near 0.80). A coverage far from 0.80 (e.g., under 0.5 or over 0.95) signals a miscalibrated quantile band — investigate before treating the artifact as ready.

- [ ] **Step 4: End-to-end smoke test via Docker Compose**

```bash
docker compose run --rm training --train data/train.csv --winkels data/store.csv
# copy the printed version into .env as MODEL_VERSION
docker compose up -d api
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/forecast \
  -H "X-API-Key: <jouw-key>" -H "Content-Type: application/json" \
  -d '{"store_id": 1, "start_datum": "2015-08-01", "horizon_dagen": 5}'
curl -s http://localhost:8000/metrics -H "X-API-Key: <jouw-key>"
docker compose down
```

Expected: `/health` returns 200 with the model version, `/forecast` returns 5 sorted p10/p50/p90 predictions, `/metrics` returns the same RMSPE/coverage seen in Step 3.

- [ ] **Step 5: Final commit**

```bash
git add -A
git status --short
```

Expected: no unexpected files (data/*.csv, models/*, .env, api_keys.json, audit.log should all be gitignored per Task 1). If everything is clean, this task needs no separate commit — it's a verification pass over what Tasks 1–19 already committed.

---

## Self-Review Notes

- **Spec coverage:** every section of the design spec (aanpak, data & model, componenten & dataflow, foutafhandeling, beveiliging, tests, deployment, openstaande risico's) maps to at least one task above; the three "openstaande risico's" (Kaggle access, dataset license, XGBoost version) are handled as explicit manual-verification steps in README.md and Task 20 rather than silently dropped.
- **Placeholder scan:** no TBD/TODO markers; every code step contains complete, runnable code; every test asserts a concrete, checkable outcome.
- **Type consistency:** verified `FEATURE_KOLOMMEN`/`DOEL_KOLOM` (defined in `training/train.py`, Task 8) are imported — not redefined — everywhere else they're used (`training/evaluate.py` Task 9, `training/artifact.py` Task 10 via `pipeline.features.MAX_HISTORIE_DAGEN`, `serving/forecast.py` Task 14). `schrijf_artefact`/`laad_artefact` signatures (Task 10) match exactly how they're called from `training/cli.py` (Task 11) and `serving/app.py` (Task 15).
