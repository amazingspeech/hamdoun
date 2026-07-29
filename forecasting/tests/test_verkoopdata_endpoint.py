"""Fase 5 NODIG 2 (afgeslankt): eigenaar-only CSV-upload van eigen
verkoopdata, per eigen winkel (GET is voor elke ingelogde gebruiker
leesbaar, net als de herbestel-prijs). Aparte fixture, geen model/artefact
nodig aangezien deze endpoints niets met voorspellen te maken hebben."""
import importlib
import sys

from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database


def _bouw_omgeving(tmp_path, monkeypatch):
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")
    (tmp_path / "models").mkdir()

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[])
    org_b = bootstrap_organisatie(engine, naam="Organisatie B", slug="org-b", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_a, email="eigenaar-a@klant.nl", wachtwoord="wachtwoord-a", rol="eigenaar")
    maak_gebruiker(engine, organisatie_id=org_a, email="lid-a@klant.nl", wachtwoord="wachtwoord-a-lid", rol="lid")
    maak_gebruiker(engine, organisatie_id=org_b, email="eigenaar-b@klant.nl", wachtwoord="wachtwoord-b", rol="eigenaar")

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
    return TestClient(module.app)


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


def _maak_eigen_winkel(client, naam="Webshop A"):
    resp = client.post("/organisatie/eigen-winkels", json={"naam": naam})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_zonder_upload_geeft_lege_lijst(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)

    resp = client.get("/organisatie/verkoopdata", params={"eigen_winkel_id": winkel_id})

    assert resp.status_code == 200
    assert resp.json() == {"rijen": []}


def test_eigenaar_kan_csv_uploaden_en_teruglezen(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    csv_inhoud = "datum,omzet\n2026-01-01,100\n2026-01-02,150.5\n"

    upload_resp = client.post(
        "/organisatie/verkoopdata",
        files={"bestand": ("verkoop.csv", csv_inhoud, "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["aantal_rijen"] == 2

    get_resp = client.get("/organisatie/verkoopdata", params={"eigen_winkel_id": winkel_id})
    assert get_resp.json() == {"rijen": [
        {"datum": "2026-01-01", "omzet": 100.0}, {"datum": "2026-01-02", "omzet": 150.5},
    ]}


def test_upload_vervangt_vorige_data(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    client.post(
        "/organisatie/verkoopdata",
        files={"bestand": ("v1.csv", "datum,omzet\n2026-01-01,100\n", "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    client.post(
        "/organisatie/verkoopdata",
        files={"bestand": ("v2.csv", "datum,omzet\n2026-02-01,200\n", "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    resp = client.get("/organisatie/verkoopdata", params={"eigen_winkel_id": winkel_id})
    assert resp.json() == {"rijen": [{"datum": "2026-02-01", "omzet": 200.0}]}


def test_lid_mag_niet_uploaden(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    client.post("/logout")
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.post(
        "/organisatie/verkoopdata",
        files={"bestand": ("verkoop.csv", "datum,omzet\n2026-01-01,100\n", "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    assert resp.status_code == 403


def test_lid_mag_verkoopdata_wel_lezen(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    client.post("/logout")
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.get("/organisatie/verkoopdata", params={"eigen_winkel_id": winkel_id})

    assert resp.status_code == 200


def test_upload_zonder_sessie_geeft_401(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.post(
        "/organisatie/verkoopdata",
        files={"bestand": ("verkoop.csv", "datum,omzet\n2026-01-01,100\n", "text/csv")},
        data={"eigen_winkel_id": "1"},
    )

    assert resp.status_code == 401


def test_ongeldige_csv_geeft_422(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)

    resp = client.post(
        "/organisatie/verkoopdata",
        files={"bestand": ("verkoop.csv", "verkeerde,kolommen\n1,2\n", "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    assert resp.status_code == 422


def test_verkoopdata_uploaden_zonder_eigen_winkel_id_faalt(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.post(
        "/organisatie/verkoopdata", files={"bestand": ("data.csv", "datum,omzet\n2026-01-01,100\n", "text/csv")}
    )

    assert resp.status_code == 422


def test_verkoopdata_uploaden_andermans_eigen_winkel_id_geeft_404(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.post(
        "/organisatie/verkoopdata",
        files={"bestand": ("data.csv", "datum,omzet\n2026-01-01,100\n", "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    assert resp.status_code == 404


def test_verkoopdata_lezen_andermans_eigen_winkel_id_geeft_404(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    client.post("/logout")
    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")

    resp = client.get("/organisatie/verkoopdata", params={"eigen_winkel_id": winkel_id})

    assert resp.status_code == 404
