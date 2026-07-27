import pytest
from pydantic import ValidationError

from serving.schemas import (
    ApiKeyAanmakenVerzoek,
    ApiKeyResponse,
    DagVoorspelling,
    FactorBijdrage,
    ForecastResponse,
    ForecastVerzoek,
    GebruikerAanmakenVerzoek,
    GebruikerResponse,
    LoginVerzoek,
    MetricsResponse,
    NieuweApiKeyResponse,
    PortfolioKpi,
    PortfolioResponse,
    WinkelResponse,
    WinkelSamenvatting,
)


def test_forecast_verzoek_accepteert_geldige_input():
    verzoek = ForecastVerzoek(store_id=1, start_datum="2015-08-01", horizon_dagen=14)
    assert verzoek.store_id == 1
    assert verzoek.horizon_dagen == 14


def test_forecast_verzoek_verwerpt_negatief_store_id():
    with pytest.raises(ValidationError):
        ForecastVerzoek(store_id=-1, start_datum="2015-08-01", horizon_dagen=14)


def test_forecast_verzoek_verwerpt_nul_horizon():
    with pytest.raises(ValidationError):
        ForecastVerzoek(store_id=1, start_datum="2015-08-01", horizon_dagen=0)


def test_forecast_response_serialiseert():
    response = ForecastResponse(
        store_id=1,
        voorspellingen=[DagVoorspelling(datum="2015-08-01", p10=100.0, p50=150.0, p90=200.0)],
    )
    data = response.model_dump(mode="json")
    assert data["voorspellingen"][0]["p50"] == 150.0


def test_forecast_response_bevat_belangrijkste_factoren():
    response = ForecastResponse(
        store_id=1,
        voorspellingen=[DagVoorspelling(datum="2015-08-01", p10=100.0, p50=150.0, p90=200.0)],
        belangrijkste_factoren=[FactorBijdrage(naam="Promotie", richting="hoger")],
    )
    assert response.model_dump()["belangrijkste_factoren"][0]["naam"] == "Promotie"


def test_forecast_response_belangrijkste_factoren_standaard_leeg():
    response = ForecastResponse(
        store_id=1,
        voorspellingen=[DagVoorspelling(datum="2015-08-01", p10=100.0, p50=150.0, p90=200.0)],
    )
    assert response.belangrijkste_factoren == []


def test_factor_bijdrage_verwerpt_ongeldige_richting():
    with pytest.raises(ValidationError):
        FactorBijdrage(naam="Promotie", richting="omhoog")


def test_winkel_response_serialiseert():
    response = WinkelResponse(extern_store_id=1, naam="Winkel Centrum")
    assert response.model_dump()["extern_store_id"] == 1


def test_winkel_response_naam_optioneel():
    response = WinkelResponse(extern_store_id=1, naam=None)
    assert response.naam is None


def test_winkel_samenvatting_serialiseert():
    samenvatting = WinkelSamenvatting(
        extern_store_id=1, naam="Winkel Centrum", totaal_p50=1000.0, totaal_p10=800.0,
        totaal_p90=1200.0, sparkline=[100.0, 200.0], afwijkend=True,
    )
    assert samenvatting.model_dump()["afwijkend"] is True


def test_portfolio_response_serialiseert():
    response = PortfolioResponse(
        winkels=[
            WinkelSamenvatting(
                extern_store_id=1, naam=None, totaal_p50=1000.0, totaal_p10=800.0,
                totaal_p90=1200.0, sparkline=[100.0], afwijkend=False,
            ),
        ],
        totaal_winkels=1115, offset=0, limiet=50,
        kpi=PortfolioKpi(totale_verwachte_omzet=1000.0, model_nauwkeurigheid_rmspe=0.13, aantal_afwijkend=0),
    )
    data = response.model_dump()
    assert data["totaal_winkels"] == 1115
    assert data["kpi"]["aantal_afwijkend"] == 0


def test_metrics_response_serialiseert():
    response = MetricsResponse(
        model_versie="20260101T000000Z", rmspe=0.12, coverage_p10_p90=0.81,
        n_observaties=1000, gevalideerde_horizon_dagen=48,
        trainingsperiode_eind="2015-06-30",
    )
    assert response.model_dump()["rmspe"] == 0.12


def test_metrics_response_bevat_trainingsperiode_eind():
    response = MetricsResponse(
        model_versie="20260101T000000Z", rmspe=0.12, coverage_p10_p90=0.81,
        n_observaties=1000, gevalideerde_horizon_dagen=48,
        trainingsperiode_eind="2015-06-30",
    )
    assert response.model_dump(mode="json")["trainingsperiode_eind"] == "2015-06-30"


def test_login_verzoek_accepteert_geldige_input():
    verzoek = LoginVerzoek(email="eigenaar@klant.nl", wachtwoord="een-goed-wachtwoord")
    assert verzoek.email == "eigenaar@klant.nl"


def test_login_verzoek_verwerpt_leeg_wachtwoord():
    with pytest.raises(ValidationError):
        LoginVerzoek(email="eigenaar@klant.nl", wachtwoord="")


def test_gebruiker_aanmaken_verzoek_verwerpt_leeg_wachtwoord():
    with pytest.raises(ValidationError):
        GebruikerAanmakenVerzoek(email="lid@klant.nl", wachtwoord="")


def test_gebruiker_response_serialiseert():
    response = GebruikerResponse(id=1, email="lid@klant.nl", rol="lid", actief=True)
    assert response.model_dump()["rol"] == "lid"


def test_api_key_aanmaken_verzoek_verwerpt_lege_naam():
    with pytest.raises(ValidationError):
        ApiKeyAanmakenVerzoek(naam="")


def test_api_key_response_serialiseert():
    response = ApiKeyResponse(id=1, naam="Kassasysteem", actief=True, aangemaakt_op="2026-07-27T12:00:00")
    assert response.model_dump()["naam"] == "Kassasysteem"


def test_nieuwe_api_key_response_bevat_ruwe_key():
    response = NieuweApiKeyResponse(id=1, naam="Kassasysteem", ruwe_key="vk_geheim")
    assert response.model_dump()["ruwe_key"] == "vk_geheim"
