"""Portfolio-dashboard item 10: eigenaar-only endpoints om per lid vast te
leggen welke winkels ze mogen zien (GET/PUT /gebruikers/{id}/winkels).
Aparte fixture van test_gebruikers_endpoint.py: die test teambeheer zelf,
dit bestand test specifiek de winkeltoewijzing eronder."""
import importlib
import sys

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.gebruiker_winkels import stel_toewijzingen_in
from db.gebruikers import maak_gebruiker
from db.schema import maak_database
from training import artifact, train


def _bouw_omgeving(tmp_path, monkeypatch):
    modellen = train.train_alle_kwantielen(pd.DataFrame({
        **{k: np.random.default_rng(1).uniform(0, 100, 200) for k in train.FEATURE_KOLOMMEN},
        "Sales": np.random.default_rng(1).uniform(500, 2000, 200),
        "Open": 1,
    }))
    stores = [1, 2, 3, 4]
    historie = pd.concat([
        pd.DataFrame({
            "Store": store, "Date": pd.date_range("2015-06-01", periods=40, freq="D"),
            "Sales": np.random.default_rng(2 + store).uniform(500, 2000, 40), "Open": 1,
        })
        for store in stores
    ], ignore_index=True)
    winkel_metadata = pd.DataFrame({"Store": stores, "CompetitionDistance": [500.0] * len(stores)})
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
    org_a = bootstrap_organisatie(engine, naam="Organisatie A", slug="org-a", store_ids=[1, 2, 3])
    org_b = bootstrap_organisatie(engine, naam="Organisatie B", slug="org-b", store_ids=[4])
    maak_gebruiker(engine, organisatie_id=org_a, email="eigenaar-a@klant.nl", wachtwoord="wachtwoord-a", rol="eigenaar")
    lid_a = maak_gebruiker(engine, organisatie_id=org_a, email="lid-a@klant.nl", wachtwoord="wachtwoord-a-lid", rol="lid")
    eigenaar_b = maak_gebruiker(
        engine, organisatie_id=org_b, email="eigenaar-b@klant.nl", wachtwoord="wachtwoord-b", rol="eigenaar"
    )

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
    return TestClient(module.app), engine, org_a, lid_a, eigenaar_b


def _inloggen(client, email, wachtwoord):
    resp = client.post("/login", json={"email": email, "wachtwoord": wachtwoord})
    assert resp.status_code == 200, resp.text


def test_eigenaar_kan_toewijzing_instellen_en_teruglezen(tmp_path, monkeypatch):
    client, _, _, lid_a, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    put_resp = client.put(f"/gebruikers/{lid_a}/winkels", json={"winkel_ids": [1, 2]})
    assert put_resp.status_code == 200
    assert set(put_resp.json()["winkel_ids"]) == {1, 2}

    get_resp = client.get(f"/gebruikers/{lid_a}/winkels")
    assert get_resp.status_code == 200
    assert set(get_resp.json()["winkel_ids"]) == {1, 2}


def test_toewijzing_instellen_vervangt_de_vorige_set(tmp_path, monkeypatch):
    client, engine, _, lid_a, _ = _bouw_omgeving(tmp_path, monkeypatch)
    stel_toewijzingen_in(engine, gebruiker_id=lid_a, extern_store_ids=[1, 2])
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.put(f"/gebruikers/{lid_a}/winkels", json={"winkel_ids": [3]})

    assert resp.status_code == 200
    assert resp.json()["winkel_ids"] == [3]


def test_lid_mag_toewijzing_niet_wijzigen(tmp_path, monkeypatch):
    client, _, _, lid_a, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "lid-a@klant.nl", "wachtwoord-a-lid")

    resp = client.put(f"/gebruikers/{lid_a}/winkels", json={"winkel_ids": [1]})

    assert resp.status_code == 403


def test_toewijzing_zonder_sessie_geeft_401(tmp_path, monkeypatch):
    client, _, _, lid_a, _ = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.get(f"/gebruikers/{lid_a}/winkels")

    assert resp.status_code == 401


def test_toewijzing_voor_andermans_gebruiker_geeft_404(tmp_path, monkeypatch):
    client, _, _, _, eigenaar_b = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.put(f"/gebruikers/{eigenaar_b}/winkels", json={"winkel_ids": [1]})

    assert resp.status_code == 404


def test_toewijzing_met_winkel_buiten_organisatie_geeft_422(tmp_path, monkeypatch):
    client, _, _, lid_a, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.put(f"/gebruikers/{lid_a}/winkels", json={"winkel_ids": [4]})

    assert resp.status_code == 422


def test_toewijzing_voor_eigenaar_zelf_geeft_422(tmp_path, monkeypatch):
    """Een eigenaar heeft altijd org-brede toegang — toewijzing is puur een
    lid-concept, dus dit is geen zinvolle actie."""
    client, engine, org_a, _, _ = _bouw_omgeving(tmp_path, monkeypatch)
    eigenaar_a_id = maak_gebruiker(
        engine, organisatie_id=org_a, email="tweede-eigenaar-a@klant.nl", wachtwoord="x", rol="eigenaar"
    )
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.put(f"/gebruikers/{eigenaar_a_id}/winkels", json={"winkel_ids": [1]})

    assert resp.status_code == 422


def test_toewijzing_instellen_komt_in_de_auditlog(tmp_path, monkeypatch):
    """Winkeltoewijzing verandert wie welke data mag zien — net zo
    controle-waardig als een cross-tenant-poging op /forecast, dus hoort
    in dezelfde auditlog terecht te komen."""
    client, _, _, lid_a, _ = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client, "eigenaar-a@klant.nl", "wachtwoord-a")

    resp = client.put(f"/gebruikers/{lid_a}/winkels", json={"winkel_ids": [1, 2]})
    assert resp.status_code == 200

    import json
    regel = json.loads((tmp_path / "audit.log").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert regel["key"] == "eigenaar-a@klant.nl"
    assert regel["doel_gebruiker_id"] == lid_a
    assert regel["winkel_ids"] == [1, 2]
    assert regel["statuscode"] == 200
