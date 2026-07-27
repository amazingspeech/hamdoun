from datetime import date

from serving.herbestel_advies_per_product import bereken_herbestel_advies_per_product


def _rijen_met_patroon(product, aantal_per_weekdag, start="2026-01-05", dagen=35):
    """start=2026-01-05 is een maandag. aantal_per_weekdag: dict weekday
    (0=maandag) -> aantal, gebruikt cyclisch over `dagen` dagen."""
    datums = [date.fromisoformat(start)]
    for _ in range(dagen - 1):
        datums.append(date.fromordinal(datums[-1].toordinal() + 1))
    return [
        {"datum": d.isoformat(), "product": product, "aantal": aantal_per_weekdag[d.weekday()]}
        for d in datums
    ]


def test_product_met_genoeg_historie_krijgt_advies():
    rijen = _rijen_met_patroon("Brood", {i: 10 for i in range(7)})

    resultaat = bereken_herbestel_advies_per_product(rijen, horizon_dagen=7, vanaf=date(2026, 2, 9))

    assert len(resultaat) == 1
    assert resultaat[0]["product"] == "Brood"
    assert resultaat[0]["aantal_p50"] == 70.0


def test_product_onder_de_drempel_wordt_overgeslagen():
    rijen = _rijen_met_patroon("Krant", {i: 5 for i in range(7)}, dagen=20)

    resultaat = bereken_herbestel_advies_per_product(rijen, horizon_dagen=7, vanaf=date(2026, 2, 9))

    assert resultaat == []


def test_meerdere_producten_elk_apart_beoordeeld():
    rijen = _rijen_met_patroon("Brood", {i: 10 for i in range(7)}) + _rijen_met_patroon(
        "Krant", {i: 5 for i in range(7)}, dagen=20
    )

    resultaat = bereken_herbestel_advies_per_product(rijen, horizon_dagen=7, vanaf=date(2026, 2, 9))

    producten = {r["product"] for r in resultaat}
    assert producten == {"Brood"}


def test_resultaat_gesorteerd_op_aflopend_verwacht_aantal():
    rijen = _rijen_met_patroon("Weinig", {i: 2 for i in range(7)}) + _rijen_met_patroon(
        "Veel", {i: 20 for i in range(7)}
    )

    resultaat = bereken_herbestel_advies_per_product(rijen, horizon_dagen=7, vanaf=date(2026, 2, 9))

    assert [r["product"] for r in resultaat] == ["Veel", "Weinig"]


def test_geen_rijen_geeft_lege_lijst():
    assert bereken_herbestel_advies_per_product([], horizon_dagen=7, vanaf=date(2026, 2, 9)) == []


def test_bandbreedte_klemt_nooit_onder_nul():
    rijen = _rijen_met_patroon("Wisselvallig", {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 20, 6: 20}, dagen=35)

    resultaat = bereken_herbestel_advies_per_product(rijen, horizon_dagen=7, vanaf=date(2026, 2, 9))

    assert resultaat[0]["aantal_p10"] >= 0
