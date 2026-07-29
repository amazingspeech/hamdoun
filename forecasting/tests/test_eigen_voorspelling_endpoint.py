"""Fase 5 NODIG 5-aanvulling: GET /organisatie/eigen-voorspelling — een
lichte voorspelling rechtstreeks uit eigen_verkoopdata, per eigen winkel,
voor organisaties zonder winkel in het gedeelde model (elke self-serve
signup). Zelfde fixture-patroon als test_verkoopdata_endpoint.py."""
import importlib
import sys
from datetime import date, timedelta

from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.eigen_winkel_instellingen import stel_prijs_in
from db.eigen_winkels import maak_eigen_winkel
from db.gebruikers import maak_gebruiker
from db.schema import maak_database
from db.verkoopdata import vervang_verkoopdata
from serving.eigen_voorspelling import MINIMUM_DAGEN


def _bouw_omgeving(tmp_path, monkeypatch):
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")
    (tmp_path / "models").mkdir()

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_a, email="eigenaar-a@klant.nl", wachtwoord="wachtwoord-a", rol="eigenaar")
    maak_gebruiker(engine, organisatie_id=org_a, email="lid-a@klant.nl", wachtwoord="wachtwoord-a-lid", rol="lid")
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_a, naam="Webshop A")

    monkeypatch.setenv("MODEL_VERSION", _bootstrap_model(tmp_path))
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
    return TestClient(module.app), engine, winkel_id


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


def _inloggen(client, email, wachtwoord):
    resp = client.post("/login", json={"email": email, "wachtwoord": wachtwoord})
    assert resp.status_code == 200, resp.text


def _upload_dagen(engine, winkel_id, aantal_dagen, omzet=100.0):
    start = date(2026, 1, 1)
    rijen = [((start + timedelta(days=i)).isoformat(), omzet) for i in range(aantal_dagen)]
    vervang_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=rijen)


def test_te_weinig_data_geeft_beschikbaar_false_met_voortgang(tmp_path, monkeypatch):
    client, engine, winkel_id = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    _upload_dagen(engine, winkel_id, aantal_dagen=10)

    resp = client.get("/organisatie/eigen-voorspelling", params={"eigen_winkel_id": winkel_id})

    assert resp.status_code == 200
    data = resp.json()
    assert data["beschikbaar"] is False
    assert data["dagen_verzameld"] == 10
    assert data["dagen_nodig"] == MINIMUM_DAGEN
    assert data["voorspellingen"] == []


def test_genoeg_data_geeft_voorspelling(tmp_path, monkeypatch):
    client, engine, winkel_id = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    _upload_dagen(engine, winkel_id, aantal_dagen=MINIMUM_DAGEN)

    resp = client.get("/organisatie/eigen-voorspelling", params={"eigen_winkel_id": winkel_id})

    assert resp.status_code == 200
    data = resp.json()
    assert data["beschikbaar"] is True
    assert len(data["voorspellingen"]) == 7
    assert data["totaal_p50"] is not None


def test_herbestel_advies_wordt_meegegeven_als_prijs_ingesteld(tmp_path, monkeypatch):
    client, engine, winkel_id = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    _upload_dagen(engine, winkel_id, aantal_dagen=MINIMUM_DAGEN, omzet=140.0)
    stel_prijs_in(engine, eigen_winkel_id=winkel_id, bedrag=14.0)

    resp = client.get("/organisatie/eigen-voorspelling", params={"eigen_winkel_id": winkel_id})

    assert resp.json()["herbestel_advies"] is not None


def test_lid_mag_eigen_voorspelling_lezen(tmp_path, monkeypatch):
    client, engine, winkel_id = _bouw_omgeving(tmp_path, monkeypatch)
    _upload_dagen(engine, winkel_id, aantal_dagen=MINIMUM_DAGEN)
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.get("/organisatie/eigen-voorspelling", params={"eigen_winkel_id": winkel_id})

    assert resp.status_code == 200
