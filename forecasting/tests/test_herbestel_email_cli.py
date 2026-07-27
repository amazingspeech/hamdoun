from serving import herbestel_email_cli


def _bootstrap_model(tmp_path):
    import numpy as np
    import pandas as pd

    from training import artifact, train

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
    return artifact.schrijf_artefact(
        basis_map=tmp_path / "models", modellen=modellen, historie=historie,
        winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.15, "coverage_p10_p90": 0.79, "n_observaties": 500},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=30, versleuteld=False,
    )


def test_main_gebruikt_dag_na_trainingsperiode_als_startdatum_niet_vandaag(tmp_path, monkeypatch):
    """Regressietest voor een productiebug: de demo/historische dataset
    eindigt lang vóór de echte kalenderdatum, dus date.today() als
    start_datum laat elke voorspelling met HorizonBuitenBereik falen. De
    interactieve dashboard-flow (serving/app.py's /portfolio-endpoint)
    gebruikt al trainingsperiode_eind + 1 dag als standaard — de cronjob
    moet dezelfde aanname volgen, niet de systeemklok."""
    import datetime as datetime_module

    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")
    (tmp_path / "models").mkdir()
    monkeypatch.setenv("MODEL_VERSION", _bootstrap_model(tmp_path))
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tmp_path / "tenants.db"))
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("MAIL_SMTP_HOST", "smtp.testomgeving.nl")

    aangeroepen_met = {}

    def _nep(engine, modellen, historie, winkel_metadata, mail_config, start_datum):
        aangeroepen_met["start_datum"] = start_datum
        return []

    monkeypatch.setattr(herbestel_email_cli, "verstuur_wekelijkse_herbestel_mails", _nep)

    herbestel_email_cli.main()

    assert aangeroepen_met["start_datum"] == datetime_module.date(2015, 7, 1)


def test_main_geeft_resultaat_van_verstuur_wekelijkse_herbestel_mails_door(tmp_path, monkeypatch):
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")
    (tmp_path / "models").mkdir()
    monkeypatch.setenv("MODEL_VERSION", _bootstrap_model(tmp_path))
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tmp_path / "tenants.db"))
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    # Expliciet een bekende waarde zetten i.p.v. delenv: serving.config.
    # laad_settings() roept load_dotenv() aan, wat een lokaal .env-bestand
    # (met eventueel al echte mailinstellingen erin, bv. tijdens
    # live-verificatie) alsnog zou inlezen als deze variabele hier
    # onbekend blijft — zie dezelfde afweging in tests/test_signup_endpoint.py.
    monkeypatch.setenv("MAIL_SMTP_HOST", "smtp.testomgeving.nl")

    aangeroepen_met = {}

    def _nep(engine, modellen, historie, winkel_metadata, mail_config, start_datum):
        aangeroepen_met["mail_config"] = mail_config
        return ["iemand@voorbeeld.nl"]

    monkeypatch.setattr(herbestel_email_cli, "verstuur_wekelijkse_herbestel_mails", _nep)

    resultaat = herbestel_email_cli.main()

    assert resultaat == ["iemand@voorbeeld.nl"]
    assert aangeroepen_met["mail_config"]["smtp_host"] == "smtp.testomgeving.nl"
