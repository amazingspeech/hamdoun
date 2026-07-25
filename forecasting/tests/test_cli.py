import numpy as np
import pandas as pd
import pytest

from training import artifact, cli


def _schrijf_synthetische_data(tmp_path, n_dagen=140, n_winkels=3):
    rng = np.random.default_rng(7)
    rijen = []
    for store in range(1, n_winkels + 1):
        datums = pd.date_range("2015-01-01", periods=n_dagen, freq="D")
        basis = 800 + store * 100
        for i, datum in enumerate(datums):
            rijen.append({
                "Store": store, "DayOfWeek": datum.dayofweek + 1, "Date": datum.strftime("%Y-%m-%d"),
                "Sales": basis + 50 * np.sin(i / 7) + rng.normal(0, 20),
                "Customers": 100, "Open": 1, "Promo": int(i % 5 == 0),
                "StateHoliday": "0", "SchoolHoliday": 0,
            })
    train_pad = tmp_path / "train.csv"
    pd.DataFrame(rijen).to_csv(train_pad, index=False)

    winkels_pad = tmp_path / "store.csv"
    pd.DataFrame({
        "Store": range(1, n_winkels + 1),
        "StoreType": ["a"] * n_winkels,
        "Assortment": ["a"] * n_winkels,
        "CompetitionDistance": [500.0 * s for s in range(1, n_winkels + 1)],
    }).to_csv(winkels_pad, index=False)

    return train_pad, winkels_pad


def test_cli_end_to_end_schrijft_artefact(tmp_path):
    train_pad, winkels_pad = _schrijf_synthetische_data(tmp_path)
    models_dir = tmp_path / "models"

    versie = cli.main([
        "--train", str(train_pad), "--winkels", str(winkels_pad), "--models-dir", str(models_dir),
    ])

    geladen = artifact.laad_artefact(models_dir, versie)
    assert set(geladen["modellen"].keys()) == {0.1, 0.5, 0.9}
    assert 0.0 <= geladen["metadata"]["metrics"]["rmspe"]
    assert geladen["metadata"]["gevalideerde_horizon_dagen"] == cli.TEST_DAGEN
