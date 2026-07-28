from datetime import date

from serving.eigen_voorspelling import MINIMUM_DAGEN, bereken_eigen_voorspelling


def _rijen_met_patroon(aantal_weken, weekday_omzet):
    """Genereert `aantal_weken` weken verkoopdata, startend op een maandag,
    waarbij elke weekdag consequent zijn eigen vaste omzet krijgt (afgezien
    van kleine variatie via de offset) — zodat een test een voorspelbaar
    dag-van-de-week-patroon kan verifiëren."""
    rijen = []
    start = date(2026, 1, 5)  # een maandag
    for week in range(aantal_weken):
        for wd in range(7):
            d = date.fromordinal(start.toordinal() + week * 7 + wd)
            rijen.append({"datum": d.isoformat(), "omzet": weekday_omzet[wd]})
    return rijen


def test_te_weinig_data_geeft_none():
    rijen = _rijen_met_patroon(2, {i: 100.0 for i in range(7)})  # 14 dagen, onder MINIMUM_DAGEN
    assert MINIMUM_DAGEN > 14

    resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=7, vanaf=date(2026, 2, 2))

    assert resultaat is None


def test_precies_minimum_dagen_geeft_wel_resultaat():
    rijen = _rijen_met_patroon(MINIMUM_DAGEN // 7, {i: 100.0 for i in range(7)})

    resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=7, vanaf=date(2026, 3, 2))

    assert resultaat is not None


def test_voorspelling_volgt_dag_van_de_week_patroon():
    # Maandag altijd 100, de rest altijd 200 — een duidelijk herkenbaar patroon.
    weekday_omzet = {0: 100.0} | {i: 200.0 for i in range(1, 7)}
    rijen = _rijen_met_patroon(6, weekday_omzet)  # 42 dagen, ruim boven het minimum

    # vanaf is een maandag
    resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=7, vanaf=date(2026, 3, 2))

    maandag = resultaat["voorspellingen"][0]
    dinsdag = resultaat["voorspellingen"][1]
    assert maandag["datum"] == "2026-03-02"
    assert maandag["p50"] == 100.0
    assert dinsdag["p50"] == 200.0


def test_p10_p50_p90_zijn_consistent_geordend():
    rijen = _rijen_met_patroon(6, {0: 90.0, 1: 110.0, 2: 100.0, 3: 105.0, 4: 95.0, 5: 120.0, 6: 80.0})

    resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=7, vanaf=date(2026, 3, 2))

    for dag in resultaat["voorspellingen"]:
        assert dag["p10"] <= dag["p50"] <= dag["p90"]


def test_totalen_zijn_som_van_de_dagen():
    rijen = _rijen_met_patroon(6, {i: 100.0 for i in range(7)})

    resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=7, vanaf=date(2026, 3, 2))

    assert resultaat["totaal_p50"] == sum(d["p50"] for d in resultaat["voorspellingen"])
    assert resultaat["totaal_p10"] == sum(d["p10"] for d in resultaat["voorspellingen"])
    assert resultaat["totaal_p90"] == sum(d["p90"] for d in resultaat["voorspellingen"])


def test_voorspelling_wordt_nooit_negatief():
    # Grillige data met een enkele uitschieter naar boven, zodat het
    # residu-op-basis-van-percentiel voor p10 flink negatief zou uitvallen
    # als er niet op 0 geklemd wordt.
    rijen = _rijen_met_patroon(4, {i: 10.0 for i in range(7)})
    rijen[0]["omzet"] = 500.0  # uitschieter op de allereerste dag

    resultaat = bereken_eigen_voorspelling(rijen, horizon_dagen=7, vanaf=date(2026, 2, 2))

    assert all(dag["p10"] >= 0 for dag in resultaat["voorspellingen"])
