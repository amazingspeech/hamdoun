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
