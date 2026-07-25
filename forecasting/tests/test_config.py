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
