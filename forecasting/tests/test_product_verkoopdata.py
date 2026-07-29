import pytest

from serving.product_verkoopdata import OngeldigeProductVerkoopdata, parse_product_verkoopdata_csv


def test_parse_product_verkoopdata_csv_leest_geldige_rijen():
    inhoud = "datum,product,aantal\n2026-01-01,Brood,10\n2026-01-01,Melk,4\n"

    rijen = parse_product_verkoopdata_csv(inhoud)

    assert rijen == [("2026-01-01", "Brood", 10), ("2026-01-01", "Melk", 4)]


def test_parse_product_verkoopdata_csv_accepteert_hoofdlettergevoelige_kolomnamen():
    inhoud = "Datum,Product,Aantal\n2026-01-01,Brood,10\n"

    rijen = parse_product_verkoopdata_csv(inhoud)

    assert rijen == [("2026-01-01", "Brood", 10)]


def test_parse_product_verkoopdata_csv_accepteert_nul_als_verplichte_rij():
    inhoud = "datum,product,aantal\n2026-01-01,Brood,0\n"

    rijen = parse_product_verkoopdata_csv(inhoud)

    assert rijen == [("2026-01-01", "Brood", 0)]


def test_parse_product_verkoopdata_csv_zonder_rijen_geeft_lege_lijst():
    assert parse_product_verkoopdata_csv("datum,product,aantal\n") == []


def test_parse_product_verkoopdata_csv_zonder_verplichte_kolommen_faalt_hard():
    with pytest.raises(OngeldigeProductVerkoopdata, match="datum.*product.*aantal"):
        parse_product_verkoopdata_csv("dag,artikel,stuks\n2026-01-01,Brood,10\n")


def test_parse_product_verkoopdata_csv_ongeldige_datum_faalt_hard():
    with pytest.raises(OngeldigeProductVerkoopdata, match="datum"):
        parse_product_verkoopdata_csv("datum,product,aantal\n01-01-2026,Brood,10\n")


def test_parse_product_verkoopdata_csv_leeg_productnaam_faalt_hard():
    with pytest.raises(OngeldigeProductVerkoopdata, match="product"):
        parse_product_verkoopdata_csv("datum,product,aantal\n2026-01-01,,10\n")


def test_parse_product_verkoopdata_csv_ongeldig_aantal_faalt_hard():
    with pytest.raises(OngeldigeProductVerkoopdata, match="aantal"):
        parse_product_verkoopdata_csv("datum,product,aantal\n2026-01-01,Brood,niet-een-getal\n")


def test_parse_product_verkoopdata_csv_negatief_aantal_faalt_hard():
    with pytest.raises(OngeldigeProductVerkoopdata, match="aantal"):
        parse_product_verkoopdata_csv("datum,product,aantal\n2026-01-01,Brood,-5\n")


def test_parse_product_verkoopdata_csv_niet_heel_getal_faalt_hard():
    with pytest.raises(OngeldigeProductVerkoopdata, match="aantal"):
        parse_product_verkoopdata_csv("datum,product,aantal\n2026-01-01,Brood,3.5\n")


def test_parse_product_verkoopdata_csv_dubbele_datum_product_combinatie_faalt_hard():
    with pytest.raises(OngeldigeProductVerkoopdata, match="dubbel"):
        parse_product_verkoopdata_csv("datum,product,aantal\n2026-01-01,Brood,10\n2026-01-01,Brood,5\n")


def test_parse_product_verkoopdata_csv_zelfde_datum_ander_product_mag():
    inhoud = "datum,product,aantal\n2026-01-01,Brood,10\n2026-01-01,Melk,4\n"

    rijen = parse_product_verkoopdata_csv(inhoud)

    assert len(rijen) == 2


def test_parse_product_verkoopdata_csv_accepteert_puntkomma_als_scheidingsteken():
    inhoud = "datum;product;aantal\n2026-01-01;Brood;10\n2026-01-01;Melk;4\n"

    rijen = parse_product_verkoopdata_csv(inhoud)

    assert rijen == [("2026-01-01", "Brood", 10), ("2026-01-01", "Melk", 4)]
