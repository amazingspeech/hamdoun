"""Fase 4 Stap 5: meerdere gebruikers per organisatie, eigenaar/lid-rolmodel.
Aparte fixture van test_login.py: die test één gebruiker, dit bestand test
expliciet eigenaar- vs. lid-rechten en organisatie-isolatie tussen twee
klanten' gebruikerslijsten."""
import importlib
import sys

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database
from training import artifact, train


def _bouw_gebruikers_omgeving(tmp_path, monkeypatch):
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
    return TestClient(module.app)


def _inloggen(client, email, wachtwoord):
    resp = client.post("/login", json={"email": email, "wachtwoord": wachtwoord})
    assert resp.status_code == 200, resp.text


def test_eigenaar_kan_gebruiker_aanmaken_in_eigen_organisatie(tmp_path, monkeypatch):
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.post("/gebruikers", json={"email": "nieuw-lid@klant.nl", "wachtwoord": "een-nieuw-wachtwoord"})

    assert resp.status_code == 201
    assert resp.json()["rol"] == "lid"
    assert resp.json()["email"] == "nieuw-lid@klant.nl"


def test_nieuw_aangemaakte_gebruiker_kan_inloggen(tmp_path, monkeypatch):
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    client.post("/gebruikers", json={"email": "nieuw-lid@klant.nl", "wachtwoord": "een-nieuw-wachtwoord"})

    resp = client.post("/login", json={"email": "nieuw-lid@klant.nl", "wachtwoord": "een-nieuw-wachtwoord"})

    assert resp.status_code == 200


def test_lid_mag_geen_gebruiker_aanmaken(tmp_path, monkeypatch):
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.post("/gebruikers", json={"email": "nog-een-lid@klant.nl", "wachtwoord": "wachtwoord"})

    assert resp.status_code == 403


def test_gebruiker_aanmaken_zonder_sessie_geeft_401(tmp_path, monkeypatch):
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)

    resp = client.post("/gebruikers", json={"email": "nieuw-lid@klant.nl", "wachtwoord": "wachtwoord"})

    assert resp.status_code == 401


def test_gebruiker_aanmaken_met_bestaand_email_geeft_409(tmp_path, monkeypatch):
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.post("/gebruikers", json={"email": "lid-a@klant.nl", "wachtwoord": "wachtwoord"})

    assert resp.status_code == 409


def test_gebruikerslijst_toont_alleen_eigen_organisatie(tmp_path, monkeypatch):
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.get("/gebruikers")

    assert resp.status_code == 200
    emails = {r["email"] for r in resp.json()}
    assert emails == {"eigenaar-a@klant.nl", "lid-a@klant.nl"}


def test_lid_kan_gebruikerslijst_bekijken(tmp_path, monkeypatch):
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.get("/gebruikers")

    assert resp.status_code == 200


def test_gebruiker_aanmaken_op_limiet_geeft_403(tmp_path, monkeypatch):
    # Bouw een eigen kleine omgeving (niet de gedeelde org_a/org_b fixture)
    # zodat ingekochte_leden expliciet op 1 gezet kan worden.
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


def test_eigenaar_kan_lid_verwijderen(tmp_path, monkeypatch):
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    lid_id = client.post("/gebruikers", json={"email": "tijdelijk-lid@klant.nl", "wachtwoord": "een-nieuw-wachtwoord"}).json()["id"]

    resp = client.delete(f"/gebruikers/{lid_id}")

    assert resp.status_code == 204
    lijst = client.get("/gebruikers").json()
    verwijderd = next(g for g in lijst if g["id"] == lid_id)
    assert verwijderd["actief"] is False


def test_verwijderen_van_andermans_lid_geeft_404(tmp_path, monkeypatch):
    client = _bouw_gebruikers_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    lid_id = client.post("/gebruikers", json={"email": "tijdelijk-lid@klant.nl", "wachtwoord": "een-nieuw-wachtwoord"}).json()["id"]
    client.post("/logout")

    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")
    resp = client.delete(f"/gebruikers/{lid_id}")

    assert resp.status_code == 404


def test_verwijderen_vrijgemaakte_seat_kan_opnieuw_gebruikt_worden(tmp_path, monkeypatch):
    from db.bootstrap import bootstrap_organisatie
    from db.gebruikers import maak_gebruiker
    from db.schema import maak_database
    import sys
    import importlib
    from fastapi.testclient import TestClient
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
    org_id = bootstrap_organisatie(engine, naam="Beperkte Klant", slug="beperkte-klant", store_ids=[], ingekochte_leden=2)
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
    eerste_lid = client.post("/gebruikers", json={"email": "eerste-lid@klant.nl", "wachtwoord": "een-nieuw-wachtwoord"})
    assert eerste_lid.status_code == 201
    geblokkeerd = client.post("/gebruikers", json={"email": "tweede-lid@klant.nl", "wachtwoord": "een-nieuw-wachtwoord"})
    assert geblokkeerd.status_code == 403

    client.delete(f"/gebruikers/{eerste_lid.json()['id']}")

    opnieuw = client.post("/gebruikers", json={"email": "derde-lid@klant.nl", "wachtwoord": "een-nieuw-wachtwoord"})
    assert opnieuw.status_code == 201
