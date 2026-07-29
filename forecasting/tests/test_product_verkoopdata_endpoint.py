"""Herbestel-advies per product (premium, self-serve-only), per eigen
winkel. Zelfde fixture-vorm als test_verkoopdata_endpoint.py — die
endpoints bestaan al, dit dekt de per-product-variant + de premium-gate."""
import importlib
import sys
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database
from db.schema import organisaties as organisaties_tabel


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
    return TestClient(module.app), engine


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


def _zet_in_proefperiode(engine, slug="org-a"):
    with engine.begin() as conn:
        org_id = conn.execute(select(organisaties_tabel.c.id).where(organisaties_tabel.c.slug == slug)).scalar_one()
        conn.execute(
            organisaties_tabel.update().where(organisaties_tabel.c.id == org_id).values(
                trial_verloopt_op=datetime.now(timezone.utc) + timedelta(days=14)
            )
        )


def _geldige_csv_35_dagen():
    regels = ["datum,product,aantal"]
    for i in range(35):
        d = f"2026-01-{i + 1:02d}" if i < 31 else f"2026-02-{i - 30:02d}"
        regels.append(f"{d},Brood,10")
    return "\n".join(regels) + "\n"


def test_eigenaar_kan_csv_uploaden_en_teruglezen(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    csv_inhoud = "datum,product,aantal\n2026-01-01,Brood,10\n2026-01-01,Melk,4\n"

    upload_resp = client.post(
        "/organisatie/product-verkoopdata",
        files={"bestand": ("verkoop.csv", csv_inhoud, "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    assert upload_resp.status_code == 200, upload_resp.text
    assert upload_resp.json()["aantal_rijen"] == 2


def test_lid_mag_niet_uploaden(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    client.post("/logout")
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.post(
        "/organisatie/product-verkoopdata",
        files={"bestand": ("verkoop.csv", "datum,product,aantal\n2026-01-01,Brood,10\n", "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    assert resp.status_code == 403


def test_ongeldige_csv_geeft_422(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)

    resp = client.post(
        "/organisatie/product-verkoopdata",
        files={"bestand": ("verkoop.csv", "verkeerde,kolommen\n1,2\n", "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    assert resp.status_code == 422


def test_advies_geeft_lege_lijst_zonder_genoeg_historie(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    client.post(
        "/organisatie/product-verkoopdata",
        files={"bestand": ("v.csv", "datum,product,aantal\n2026-01-01,Brood,10\n", "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    resp = client.get("/organisatie/herbestel-advies-per-product", params={"eigen_winkel_id": winkel_id})

    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_advies_met_genoeg_historie(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    client.post(
        "/organisatie/product-verkoopdata",
        files={"bestand": ("v.csv", _geldige_csv_35_dagen(), "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    resp = client.get("/organisatie/herbestel-advies-per-product", params={"eigen_winkel_id": winkel_id})

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["product"] == "Brood"
    assert items[0]["aantal_p50"] > 0


def test_eigenaar_in_proefperiode_mag_niet_uploaden(tmp_path, monkeypatch):
    client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    _zet_in_proefperiode(engine)

    resp = client.post(
        "/organisatie/product-verkoopdata",
        files={"bestand": ("v.csv", "datum,product,aantal\n2026-01-01,Brood,10\n", "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )

    assert resp.status_code == 403
    assert "proefperiode" in resp.json()["detail"].lower()


def test_advies_niet_beschikbaar_tijdens_proefperiode(tmp_path, monkeypatch):
    client, engine = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    client.post(
        "/organisatie/product-verkoopdata",
        files={"bestand": ("v.csv", _geldige_csv_35_dagen(), "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )
    _zet_in_proefperiode(engine)

    resp = client.get("/organisatie/herbestel-advies-per-product", params={"eigen_winkel_id": winkel_id})

    assert resp.status_code == 403
    assert "proefperiode" in resp.json()["detail"].lower()


def test_product_verkoopdata_endpoint_isoleert_tussen_organisaties(tmp_path, monkeypatch):
    client, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")
    winkel_id = _maak_eigen_winkel(client)
    client.post(
        "/organisatie/product-verkoopdata",
        files={"bestand": ("v.csv", _geldige_csv_35_dagen(), "text/csv")},
        data={"eigen_winkel_id": str(winkel_id)},
    )
    client.post("/logout")

    _inloggen(client, "eigenaar-b@klant.nl", "wachtwoord-b")
    resp = client.get("/organisatie/herbestel-advies-per-product", params={"eigen_winkel_id": winkel_id})

    assert resp.status_code == 404
