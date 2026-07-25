"""Command-line entry point: draait de volledige pipeline + training +
evaluatie + artefact-oplevering in één commando.

Gebruik: python3 -m training.cli --train data/train.csv --winkels data/store.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.features import bouw_features
from pipeline.ingest import laad_train, laad_winkels, samenvoegen
from pipeline.split import walk_forward_split
from training.artifact import bewaar_historie, bewaar_winkel_metadata, schrijf_artefact
from training.evaluate import evalueer
from training.train import train_alle_kwantielen

VALIDATIE_DAGEN = 48
TEST_DAGEN = 48


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--winkels", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--encrypt", action="store_true")
    args = parser.parse_args(argv)

    transacties = laad_train(args.train)
    winkels = laad_winkels(args.winkels)
    samengevoegd = samenvoegen(transacties, winkels)
    met_features = bouw_features(samengevoegd)

    train_df, _validatie, test_df = walk_forward_split(met_features, VALIDATIE_DAGEN, TEST_DAGEN)

    modellen = train_alle_kwantielen(train_df)
    metrics = evalueer(modellen, test_df)
    print(f"RMSPE: {metrics['rmspe']:.4f}  coverage p10-p90: {metrics['coverage_p10_p90']:.2%}")

    historie = bewaar_historie(met_features, tot_en_met=train_df["Date"].max())
    winkel_metadata = bewaar_winkel_metadata(winkels)

    versie = schrijf_artefact(
        basis_map=args.models_dir,
        modellen=modellen,
        historie=historie,
        winkel_metadata=winkel_metadata,
        metrics=metrics,
        trainingsperiode=(train_df["Date"].min(), train_df["Date"].max()),
        gevalideerde_horizon_dagen=TEST_DAGEN,
        versleuteld=args.encrypt,
    )
    print(f"Artefact weggeschreven als versie: {versie}")
    print(f"Zet MODEL_VERSION={versie} in .env om deze versie te serveren.")
    return versie


if __name__ == "__main__":
    main()
