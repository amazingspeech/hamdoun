import base64

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
