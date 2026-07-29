import pytest

from serving.verkoopdata import OngeldigeVerkoopdata, parse_verkoopdata_csv


def test_parse_verkoopdata_csv_leest_geldige_rijen():
    inhoud = "datum,omzet\n2026-01-01,120.5\n2026-01-02,98\n"

    rijen = parse_verkoopdata_csv(inhoud)

    assert rijen == [("2026-01-01", 120.5), ("2026-01-02", 98.0)]


def test_parse_verkoopdata_csv_accepteert_hoofdlettergevoelige_kolomnamen():
    inhoud = "Datum,Omzet\n2026-01-01,120.5\n"

    rijen = parse_verkoopdata_csv(inhoud)

    assert rijen == [("2026-01-01", 120.5)]


def test_parse_verkoopdata_csv_zonder_rijen_geeft_lege_lijst():
    assert parse_verkoopdata_csv("datum,omzet\n") == []


def test_parse_verkoopdata_csv_zonder_verplichte_kolommen_faalt_hard():
    with pytest.raises(OngeldigeVerkoopdata, match="datum.*omzet"):
        parse_verkoopdata_csv("dag,bedrag\n2026-01-01,120.5\n")


def test_parse_verkoopdata_csv_ongeldige_datum_faalt_hard():
    with pytest.raises(OngeldigeVerkoopdata, match="datum"):
        parse_verkoopdata_csv("datum,omzet\n01-01-2026,120.5\n")


def test_parse_verkoopdata_csv_ongeldig_omzetgetal_faalt_hard():
    with pytest.raises(OngeldigeVerkoopdata, match="omzet"):
        parse_verkoopdata_csv("datum,omzet\n2026-01-01,niet-een-getal\n")


def test_parse_verkoopdata_csv_negatieve_omzet_faalt_hard():
    with pytest.raises(OngeldigeVerkoopdata, match="omzet"):
        parse_verkoopdata_csv("datum,omzet\n2026-01-01,-5\n")


def test_parse_verkoopdata_csv_dubbele_datum_faalt_hard():
    with pytest.raises(OngeldigeVerkoopdata, match="dubbel"):
        parse_verkoopdata_csv("datum,omzet\n2026-01-01,100\n2026-01-01,200\n")


def test_parse_verkoopdata_csv_accepteert_puntkomma_als_scheidingsteken():
    inhoud = "datum;omzet\n2026-01-01;120.5\n2026-01-02;98\n"

    rijen = parse_verkoopdata_csv(inhoud)

    assert rijen == [("2026-01-01", 120.5), ("2026-01-02", 98.0)]
