from datetime import date

import numpy as np
import pandas as pd

from db.bootstrap import bootstrap_organisatie
from db.eigen_winkels import maak_eigen_winkel
from db.gebruikers import maak_gebruiker
from db.organisaties import stel_gemiddelde_omzet_per_stuk_in
from db.schema import maak_database
from db.verkoopdata import vervang_verkoopdata
from serving.eigen_voorspelling import MINIMUM_DAGEN
from serving.herbestel_email import bouw_email_inhoud, verstuur_wekelijkse_herbestel_mails


class _ConstantModel:
    def __init__(self, waarde):
        self.waarde = waarde

    def predict(self, X):
        return np.full(len(X), self.waarde)


def _historie(store_id=1, n_dagen=40, waarde=1000.0):
    datums = pd.date_range("2015-06-01", periods=n_dagen, freq="D")
    return pd.DataFrame({
        "Store": store_id, "Date": datums, "Sales": waarde, "Open": 1,
        "DayOfWeek": [d.dayofweek + 1 for d in datums], "Promo": 0, "SchoolHoliday": 0,
    })


def _winkel_metadata(store_id=1):
    return pd.DataFrame({"Store": [store_id], "CompetitionDistance": [500.0]})


MAIL_CONFIG = {
    "smtp_host": "smtp.test.nl", "smtp_poort": 587, "afzender": "info@test.nl",
    "smtp_gebruiker": "info@test.nl", "smtp_wachtwoord": "geheim",
}


def test_bouw_email_inhoud_zonder_eigen_winkels():
    gedeeld_model_forecast = {"totaal_p10": 900.0, "totaal_p50": 1000.0, "totaal_p90": 1100.0}
    onderwerp, tekst = bouw_email_inhoud("Bakkerij De Vries", gedeeld_model_forecast, [])
    assert "Bakkerij De Vries" in onderwerp
    assert "1.000" in tekst or "1000" in tekst
    assert "stuks" not in tekst


def test_bouw_email_inhoud_met_herbestel_advies_per_eigen_winkel():
    sectie = {
        "naam": "Webshop A", "totaal_p10": 900.0, "totaal_p50": 1000.0, "totaal_p90": 1100.0,
        "advies": {"stuks_p10": 60, "stuks_p50": 67, "stuks_p90": 73},
    }
    onderwerp, tekst = bouw_email_inhoud("Bakkerij De Vries", None, [sectie])
    assert "Webshop A" in tekst
    assert "67 stuks" in tekst
    assert "73 stuks" in tekst
    assert "60 stuks" in tekst


def test_bouw_email_inhoud_meerdere_eigen_winkels_krijgen_eigen_sectie():
    secties = [
        {"naam": "Webshop A", "totaal_p10": 90.0, "totaal_p50": 100.0, "totaal_p90": 110.0, "advies": None},
        {"naam": "Marktkraam", "totaal_p10": 190.0, "totaal_p50": 200.0, "totaal_p90": 210.0, "advies": None},
    ]
    _, tekst = bouw_email_inhoud("Bakkerij De Vries", None, secties)
    assert "Webshop A" in tekst
    assert "Marktkraam" in tekst


def test_organisatie_met_gedeeld_model_winkel_krijgt_mail(tmp_path, monkeypatch):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Tessar Demo", slug="tessar-demo", store_ids=[1])
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@tessar.nl", wachtwoord="x", rol="eigenaar")

    verzonden = []
    monkeypatch.setattr(
        "serving.herbestel_email.mail.verstuur",
        lambda **kwargs: verzonden.append(kwargs["ontvanger"]),
    )

    resultaat = verstuur_wekelijkse_herbestel_mails(
        engine, modellen={q: _ConstantModel(1000.0) for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        mail_config=MAIL_CONFIG, start_datum=date(2015, 7, 11),
    )

    assert resultaat == ["eigenaar@tessar.nl"]
    assert verzonden == ["eigenaar@tessar.nl"]


def test_organisatie_zonder_winkel_maar_met_eigen_verkoopdata_krijgt_mail(tmp_path, monkeypatch):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="devries@voorbeeld.nl", wachtwoord="x", rol="eigenaar")
    winkel_id = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop")
    start = date(2026, 1, 1)
    rijen = [((start + pd.Timedelta(days=i)).isoformat(), 100.0) for i in range(MINIMUM_DAGEN)]
    vervang_verkoopdata(engine, eigen_winkel_id=winkel_id, rijen=rijen)

    verzonden = []
    monkeypatch.setattr(
        "serving.herbestel_email.mail.verstuur",
        lambda **kwargs: verzonden.append(kwargs["ontvanger"]),
    )

    resultaat = verstuur_wekelijkse_herbestel_mails(
        engine, modellen={q: _ConstantModel(1000.0) for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        mail_config=MAIL_CONFIG, start_datum=date(2026, 3, 2),
    )

    assert resultaat == ["devries@voorbeeld.nl"]


def test_organisatie_zonder_winkel_en_zonder_genoeg_eigen_data_wordt_overgeslagen(tmp_path, monkeypatch):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Net Aangemeld", slug="net-aangemeld", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="net@voorbeeld.nl", wachtwoord="x", rol="eigenaar")

    verzonden = []
    monkeypatch.setattr(
        "serving.herbestel_email.mail.verstuur",
        lambda **kwargs: verzonden.append(kwargs["ontvanger"]),
    )

    resultaat = verstuur_wekelijkse_herbestel_mails(
        engine, modellen={q: _ConstantModel(1000.0) for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        mail_config=MAIL_CONFIG, start_datum=date(2026, 3, 2),
    )

    assert resultaat == []
    assert verzonden == []


def test_organisatie_met_meerdere_eigen_winkels_krijgt_eigen_sectie_per_winkel(tmp_path, monkeypatch):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Bakkerij De Vries", slug="bakkerij-de-vries", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="devries@voorbeeld.nl", wachtwoord="x", rol="eigenaar")
    winkel_a = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Webshop A")
    winkel_b = maak_eigen_winkel(engine, organisatie_id=org_id, naam="Marktkraam")
    start = date(2026, 1, 1)
    rijen = [((start + pd.Timedelta(days=i)).isoformat(), 100.0) for i in range(MINIMUM_DAGEN)]
    vervang_verkoopdata(engine, eigen_winkel_id=winkel_a, rijen=rijen)
    vervang_verkoopdata(engine, eigen_winkel_id=winkel_b, rijen=rijen)

    verzonden_teksten = []
    monkeypatch.setattr(
        "serving.herbestel_email.mail.verstuur",
        lambda **kwargs: verzonden_teksten.append(kwargs["tekst"]),
    )

    resultaat = verstuur_wekelijkse_herbestel_mails(
        engine, modellen={q: _ConstantModel(1000.0) for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        mail_config=MAIL_CONFIG, start_datum=date(2026, 3, 2),
    )

    # Eén mail voor de hele organisatie, niet twee — met beide winkelnamen
    # als aparte secties, niet opgeteld tot één cijfer.
    assert resultaat == ["devries@voorbeeld.nl"]
    assert len(verzonden_teksten) == 1
    assert "Webshop A" in verzonden_teksten[0]
    assert "Marktkraam" in verzonden_teksten[0]


def test_herbestel_advies_wordt_meegenomen_als_prijs_ingesteld(tmp_path, monkeypatch):
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Tessar Demo", slug="tessar-demo", store_ids=[1])
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@tessar.nl", wachtwoord="x", rol="eigenaar")
    stel_gemiddelde_omzet_per_stuk_in(engine, organisatie_id=org_id, bedrag=10.0)

    verzonden_teksten = []
    monkeypatch.setattr(
        "serving.herbestel_email.mail.verstuur",
        lambda **kwargs: verzonden_teksten.append(kwargs["tekst"]),
    )

    verstuur_wekelijkse_herbestel_mails(
        engine, modellen={q: _ConstantModel(1000.0) for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        mail_config=MAIL_CONFIG, start_datum=date(2015, 7, 11),
    )

    assert "stuks" in verzonden_teksten[0]


def test_organisatie_zonder_eigenaar_wordt_overgeslagen(tmp_path, monkeypatch):
    engine = maak_database(tmp_path / "tenants.db")
    bootstrap_organisatie(engine, naam="Tessar Demo", slug="tessar-demo", store_ids=[1])
    # Geen gebruiker aangemaakt — geen eigenaar om naar te mailen.

    verzonden = []
    monkeypatch.setattr(
        "serving.herbestel_email.mail.verstuur",
        lambda **kwargs: verzonden.append(kwargs["ontvanger"]),
    )

    resultaat = verstuur_wekelijkse_herbestel_mails(
        engine, modellen={q: _ConstantModel(1000.0) for q in (0.1, 0.5, 0.9)},
        historie=_historie(), winkel_metadata=_winkel_metadata(),
        mail_config=MAIL_CONFIG, start_datum=date(2015, 7, 11),
    )

    assert resultaat == []


def test_winkel_zonder_genoeg_historie_blokkeert_niet_de_rest_van_de_organisatie(tmp_path, monkeypatch):
    """Regressietest voor een productiebug: bij een organisatie met veel
    winkels (bv. het gedeelde Rossmann-model met 1115 winkels) mist er
    vrijwel altijd wel één winkel genoeg historie voor de gekozen
    startdatum (HorizonBuitenBereik) — bv. een winkel die net geopend is
    of een lange sluiting had. Zonder per-winkel foutafhandeling crasht dat
    de hele wekelijkse cronrun voor élke organisatie, wat de docstring van
    verstuur_wekelijkse_herbestel_mails expliciet belooft te voorkomen."""
    engine = maak_database(tmp_path / "tenants.db")
    org_id = bootstrap_organisatie(engine, naam="Tessar Demo", slug="tessar-demo", store_ids=[1, 2])
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@tessar.nl", wachtwoord="x", rol="eigenaar")

    verzonden = []
    monkeypatch.setattr(
        "serving.herbestel_email.mail.verstuur",
        lambda **kwargs: verzonden.append(kwargs["ontvanger"]),
    )

    # Winkel 2 komt helemaal niet voor in de historie — precies de situatie
    # die HorizonBuitenBereik veroorzaakt (geen lag-features te berekenen).
    resultaat = verstuur_wekelijkse_herbestel_mails(
        engine, modellen={q: _ConstantModel(1000.0) for q in (0.1, 0.5, 0.9)},
        historie=_historie(store_id=1), winkel_metadata=_winkel_metadata(store_id=1),
        mail_config=MAIL_CONFIG, start_datum=date(2015, 7, 11),
    )

    assert resultaat == ["eigenaar@tessar.nl"]
    assert verzonden == ["eigenaar@tessar.nl"]


def test_mislukte_mail_voor_een_org_blokkeert_de_rest_niet(tmp_path, monkeypatch):
    engine = maak_database(tmp_path / "tenants.db")
    org_a = bootstrap_organisatie(engine, naam="Org A", slug="org-a", store_ids=[1])
    maak_gebruiker(engine, organisatie_id=org_a, email="a@voorbeeld.nl", wachtwoord="x", rol="eigenaar")
    org_b = bootstrap_organisatie(engine, naam="Org B", slug="org-b", store_ids=[2])
    maak_gebruiker(engine, organisatie_id=org_b, email="b@voorbeeld.nl", wachtwoord="x", rol="eigenaar")

    def _nep_verstuur(**kwargs):
        if kwargs["ontvanger"] == "a@voorbeeld.nl":
            raise RuntimeError("gesimuleerde SMTP-storing")

    monkeypatch.setattr("serving.herbestel_email.mail.verstuur", _nep_verstuur)

    historie_twee_winkels = pd.concat([_historie(store_id=1), _historie(store_id=2)], ignore_index=True)
    winkel_metadata_twee = pd.concat([_winkel_metadata(store_id=1), _winkel_metadata(store_id=2)], ignore_index=True)

    resultaat = verstuur_wekelijkse_herbestel_mails(
        engine, modellen={q: _ConstantModel(1000.0) for q in (0.1, 0.5, 0.9)},
        historie=historie_twee_winkels, winkel_metadata=winkel_metadata_twee,
        mail_config=MAIL_CONFIG, start_datum=date(2015, 7, 11),
    )

    assert resultaat == ["b@voorbeeld.nl"]
