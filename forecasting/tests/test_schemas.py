import pytest
from pydantic import ValidationError

from serving.schemas import DagVoorspelling, ForecastResponse, ForecastVerzoek, LoginVerzoek, MetricsResponse


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
