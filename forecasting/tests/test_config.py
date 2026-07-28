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


def test_laad_settings_zonder_mailconfig_geeft_none(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path)
    for var in ("MAIL_SMTP_HOST", "MAIL_SMTP_POORT", "MAIL_AFZENDER", "MAIL_SMTP_GEBRUIKER", "MAIL_SMTP_WACHTWOORD"):
        monkeypatch.delenv(var, raising=False)
    settings = config.laad_settings()
    assert settings.mail_smtp_host is None
    assert settings.mail_smtp_poort is None
    assert settings.mail_afzender is None
    assert settings.mail_smtp_gebruiker is None
    assert settings.mail_smtp_wachtwoord is None


def test_laad_settings_leest_mailconfig(monkeypatch, tmp_path):
    _basis_env(
        monkeypatch, tmp_path,
        MAIL_SMTP_HOST="smtp.zoho.eu", MAIL_SMTP_POORT="587", MAIL_AFZENDER="info@tessar.nl",
        MAIL_SMTP_GEBRUIKER="info@tessar.nl", MAIL_SMTP_WACHTWOORD="geheim",
    )
    settings = config.laad_settings()
    assert settings.mail_smtp_host == "smtp.zoho.eu"
    assert settings.mail_smtp_poort == 587
    assert settings.mail_afzender == "info@tessar.nl"
    assert settings.mail_smtp_gebruiker == "info@tessar.nl"
    assert settings.mail_smtp_wachtwoord == "geheim"


def test_laad_settings_docs_staan_standaard_uit(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path)
    monkeypatch.delenv("EXPOSE_API_DOCS", raising=False)
    settings = config.laad_settings()
    assert settings.expose_docs is False


def test_laad_settings_docs_aan_via_expliciete_opt_in(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path, EXPOSE_API_DOCS="true")
    settings = config.laad_settings()
    assert settings.expose_docs is True


def test_laad_settings_tenants_db_pad_default(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path)
    monkeypatch.delenv("TENANTS_DB_PAD", raising=False)
    settings = config.laad_settings()
    assert str(settings.tenants_db_pad) == "tenants.db"


def test_laad_settings_tenants_db_pad_expliciet(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path, TENANTS_DB_PAD=str(tmp_path / "eigen.db"))
    settings = config.laad_settings()
    assert str(settings.tenants_db_pad) == str(tmp_path / "eigen.db")


def test_laad_settings_sessie_cookie_secure_staat_standaard_aan(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path)
    monkeypatch.delenv("SESSIE_COOKIE_SECURE", raising=False)
    settings = config.laad_settings()
    assert settings.sessie_cookie_secure is True


def test_laad_settings_sessie_cookie_secure_expliciet_uit(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path, SESSIE_COOKIE_SECURE="false")
    settings = config.laad_settings()
    assert settings.sessie_cookie_secure is False


def test_laad_settings_zonder_stripeconfig_geeft_none(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path)
    for var in ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_ID", "APP_BASIS_URL"):
        monkeypatch.delenv(var, raising=False)
    settings = config.laad_settings()
    assert settings.stripe_secret_key is None
    assert settings.stripe_webhook_secret is None
    assert settings.stripe_price_id is None
    assert settings.app_basis_url is None


def test_laad_settings_leest_stripeconfig(monkeypatch, tmp_path):
    _basis_env(
        monkeypatch, tmp_path,
        STRIPE_SECRET_KEY="sk_test_geheim", STRIPE_WEBHOOK_SECRET="whsec_geheim",
        STRIPE_PRICE_ID="price_abc", APP_BASIS_URL="http://127.0.0.1:8000",
    )
    settings = config.laad_settings()
    assert settings.stripe_secret_key == "sk_test_geheim"
    assert settings.stripe_webhook_secret == "whsec_geheim"
    assert settings.stripe_price_id == "price_abc"
    assert settings.app_basis_url == "http://127.0.0.1:8000"


def test_laad_settings_zonder_voorbeeld_store_id_geeft_none(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path)
    monkeypatch.delenv("VOORBEELD_STORE_ID", raising=False)
    settings = config.laad_settings()
    assert settings.voorbeeld_store_id is None


def test_laad_settings_leest_voorbeeld_store_id(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path, VOORBEELD_STORE_ID="1")
    settings = config.laad_settings()
    assert settings.voorbeeld_store_id == 1


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
