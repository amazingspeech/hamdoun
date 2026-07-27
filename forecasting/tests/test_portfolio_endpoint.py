"""GET /portfolio: geaggregeerd overzicht over de winkels van een
organisatie, met paginering — een volledige live-berekening voor alle
1115 winkels van de lokale demo-organisatie kost ~88 seconden (gemeten),
dus dit endpoint berekent alleen de opgevraagde pagina, nooit het hele
portfolio in één keer."""
import importlib
import sys

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database
from training import artifact, train


def _bouw_omgeving(tmp_path, monkeypatch, org_a_stores=(1, 2, 3), org_b_stores=(4, 5)):
    modellen = train.train_alle_kwantielen(pd.DataFrame({
        **{k: np.random.default_rng(1).uniform(0, 100, 200) for k in train.FEATURE_KOLOMMEN},
        "Sales": np.random.default_rng(1).uniform(500, 2000, 200),
        "Open": 1,
    }))
    alle_stores = list(org_a_stores) + list(org_b_stores)
    historie = pd.concat([
        pd.DataFrame({
            "Store": store, "Date": pd.date_range("2015-06-01", periods=40, freq="D"),
            "Sales": np.random.default_rng(store).uniform(500, 2000, 40), "Open": 1,
        })
        for store in alle_stores
    ], ignore_index=True)
    winkel_metadata = pd.DataFrame({"Store": alle_stores, "CompetitionDistance": [500.0] * len(alle_stores)})
    versie = artifact.schrijf_artefact(
        basis_map=tmp_path / "models", modellen=modellen, historie=historie,
        winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.15, "coverage_p10_p90": 0.79, "n_observaties": 500},
        # trainingsperiode_eind moet écht overeenkomen met het laatste jaar
        # dat de historie hierboven dekt (2015-06-01 + 40 dagen = 2015-07-10):
        # /portfolio leidt start_datum af als trainingsperiode_eind + 1 dag,
        # anders overlapt die datum met bestaande historie i.p.v. erna te
        # vallen, wat HorizonBuitenBereik veroorzaakt.
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-07-10")),
        gevalideerde_horizon_dagen=30, versleuteld=False,
    )
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=list(org_a_stores))
    org_b = bootstrap_organisatie(engine, naam="Organisatie B", slug="org-b", store_ids=list(org_b_stores))
    maak_gebruiker(engine, organisatie_id=org_a, email="eigenaar-a@klant.nl", wachtwoord="wachtwoord-a")
    maak_gebruiker(engine, organisatie_id=org_b, email="eigenaar-b@klant.nl", wachtwoord="wachtwoord-b")

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
    return TestClient(module.app)


def _inloggen(client, email, wachtwoord):
    resp = client.post("/login", json={"email": email, "wachtwoord": wachtwoord})
    assert resp.status_code == 200, resp.text


def test_portfolio_geeft_alle_eigen_winkels_binnen_de_limiet(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.get("/portfolio?horizon_dagen=3&limiet=10")

    assert resp.status_code == 200
    data = resp.json()
    assert data["totaal_winkels"] == 3
    assert {w["extern_store_id"] for w in data["winkels"]} == {1, 2, 3}
    assert len(data["winkels"][0]["sparkline"]) == 3


def test_portfolio_respecteert_paginering(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    eerste_pagina = client.get("/portfolio?horizon_dagen=3&limiet=2&offset=0").json()
    tweede_pagina = client.get("/portfolio?horizon_dagen=3&limiet=2&offset=2").json()

    assert len(eerste_pagina["winkels"]) == 2
    assert len(tweede_pagina["winkels"]) == 1
    assert eerste_pagina["totaal_winkels"] == 3
    assert tweede_pagina["totaal_winkels"] == 3


def test_portfolio_kpi_bevat_totalen(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    data = client.get("/portfolio?horizon_dagen=3&limiet=10").json()

    assert data["kpi"]["totale_verwachte_omzet"] > 0
    assert data["kpi"]["model_nauwkeurigheid_rmspe"] == 0.15
    assert data["kpi"]["aantal_afwijkend"] >= 0


def test_portfolio_toont_nooit_andermans_winkels(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    data = client.get("/portfolio?horizon_dagen=3&limiet=10").json()

    assert data["totaal_winkels"] == 2
    assert {w["extern_store_id"] for w in data["winkels"]} == {4, 5}


def test_portfolio_zonder_toegang_geeft_401(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.get("/portfolio")

    assert resp.status_code == 401
