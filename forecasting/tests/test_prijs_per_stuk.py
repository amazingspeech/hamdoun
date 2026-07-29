from serving.prijs_per_stuk import bereken_gemiddelde_prijs_per_stuk


def test_berekent_prijs_uit_overlappende_dagen():
    verkoopdata = [{"datum": "2026-06-01", "omzet": 100.0}, {"datum": "2026-06-02", "omzet": 200.0}]
    product_verkoopdata = [
        {"datum": "2026-06-01", "product": "A", "aantal": 5},
        {"datum": "2026-06-02", "product": "A", "aantal": 10},
        {"datum": "2026-06-02", "product": "B", "aantal": 5},
    ]

    prijs = bereken_gemiddelde_prijs_per_stuk(verkoopdata, product_verkoopdata)

    # omzet 300 over dagen met aantal-data (300), aantal 20 stuks -> 15.0
    assert prijs == 15.0


def test_negeert_dagen_die_niet_in_beide_sets_voorkomen():
    verkoopdata = [
        {"datum": "2026-06-01", "omzet": 100.0},
        {"datum": "2026-06-02", "omzet": 999.0},  # geen aantal-data voor deze dag
    ]
    product_verkoopdata = [{"datum": "2026-06-01", "product": "A", "aantal": 10}]

    prijs = bereken_gemiddelde_prijs_per_stuk(verkoopdata, product_verkoopdata)

    assert prijs == 10.0  # 100 omzet / 10 stuks, 999/dag-2 genegeerd


def test_geen_overlappende_dagen_geeft_none():
    verkoopdata = [{"datum": "2026-06-01", "omzet": 100.0}]
    product_verkoopdata = [{"datum": "2026-06-02", "product": "A", "aantal": 10}]

    assert bereken_gemiddelde_prijs_per_stuk(verkoopdata, product_verkoopdata) is None


def test_lege_sets_geeft_none():
    assert bereken_gemiddelde_prijs_per_stuk([], []) is None


def test_nul_totaal_aantal_geeft_none():
    verkoopdata = [{"datum": "2026-06-01", "omzet": 100.0}]
    product_verkoopdata = [{"datum": "2026-06-01", "product": "A", "aantal": 0}]

    assert bereken_gemiddelde_prijs_per_stuk(verkoopdata, product_verkoopdata) is None
