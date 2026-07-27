"""Versioneren en wegschrijven van trainingsartefacten: de drie modellen, de
laatste historie per winkel (nodig om lag-features te reconstrueren bij een
voorspellingsverzoek), statische winkelmetadata, en metadata inclusief de
nauwkeurigheidscijfers. Encryptie is toggle-baar en geldt, indien aan, voor
alle bestanden in het artefact — nooit alleen voor een deel ervan."""
from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import xgboost as xgb

from pipeline.features import MAX_HISTORIE_DAGEN
from security import encryptie

HISTORIE_BUFFER_DAGEN = MAX_HISTORIE_DAGEN + 7  # marge boven de langste lag/rolling-vereiste


def nieuwe_versie_naam() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def bewaar_historie(df: pd.DataFrame, tot_en_met: pd.Timestamp) -> pd.DataFrame:
    """Bewaart per winkel alleen de laatste HISTORIE_BUFFER_DAGEN vóór
    `tot_en_met` — genoeg om lag-/rolling-features te reconstrueren, niet de
    volledige ruwe dataset."""
    grens = tot_en_met - pd.Timedelta(days=HISTORIE_BUFFER_DAGEN)
    return df[(df["Date"] > grens) & (df["Date"] <= tot_en_met)][
        ["Store", "Date", "Sales", "Open"]
    ].copy()


def bewaar_winkel_metadata(winkels: pd.DataFrame) -> pd.DataFrame:
    return winkels[["Store", "CompetitionDistance"]].copy()


def _schrijf(pad: Path, data: bytes, versleuteld: bool) -> None:
    if versleuteld:
        encryptie.schrijf_bestand(pad, data)
    else:
        pad.write_bytes(data)
        try:
            os.chmod(pad, 0o600)
        except OSError:
            pass


def _lees(pad: Path, versleuteld: bool) -> bytes:
    if versleuteld:
        return encryptie.lees_bestand(pad)
    return pad.read_bytes()


def schrijf_artefact(
    basis_map: Path,
    modellen: dict[float, xgb.XGBRegressor],
    historie: pd.DataFrame,
    winkel_metadata: pd.DataFrame,
    metrics: dict,
    trainingsperiode: tuple[pd.Timestamp, pd.Timestamp],
    gevalideerde_horizon_dagen: int,
    versleuteld: bool,
) -> str:
    """Schrijft een nieuw geversieerd artefact weg onder basis_map/<versie>/
    en geeft de versienaam terug. Bestaat de map al (zelfde seconde), dan
    wordt een teller toegevoegd om nooit een bestaand artefact te
    overschrijven."""
    basis_map.mkdir(parents=True, exist_ok=True)
    versie = nieuwe_versie_naam()
    doel = basis_map / versie
    teller = 1
    while doel.exists():
        teller += 1
        doel = basis_map / f"{versie}-{teller}"
    doel.mkdir(parents=True)

    for kwantiel, model in modellen.items():
        model_bytes = model.get_booster().save_raw(raw_format="json")
        _schrijf(doel / f"model_p{int(kwantiel * 100)}.json", bytes(model_bytes), versleuteld)

    historie_buffer = io.BytesIO()
    historie.to_parquet(historie_buffer, index=False)
    _schrijf(doel / "historie.parquet", historie_buffer.getvalue(), versleuteld)

    winkel_metadata_buffer = io.BytesIO()
    winkel_metadata.to_parquet(winkel_metadata_buffer, index=False)
    _schrijf(doel / "winkel_metadata.parquet", winkel_metadata_buffer.getvalue(), versleuteld)

    metadata = {
        "versie": doel.name,
        "aangemaakt_op": datetime.now(timezone.utc).isoformat(),
        "trainingsperiode_start": trainingsperiode[0].isoformat(),
        "trainingsperiode_eind": trainingsperiode[1].isoformat(),
        "gevalideerde_horizon_dagen": gevalideerde_horizon_dagen,
        "metrics": metrics,
    }
    _schrijf(doel / "metadata.json", json.dumps(metadata, indent=2).encode("utf-8"), versleuteld)

    return doel.name


def laad_artefact(basis_map: Path, versie: str, versleuteld: bool = False) -> dict:
    """Laadt een eerder weggeschreven artefact. Faalt hard als de versie niet
    bestaat of onvolledig is — nooit stilzwijgend een andere versie pakken."""
    doel = basis_map / versie
    if not doel.exists():
        raise RuntimeError(f"Modelversie '{versie}' bestaat niet onder {basis_map}.")

    modellen = {}
    for kwantiel in (0.1, 0.5, 0.9):
        model_pad = doel / f"model_p{int(kwantiel * 100)}.json"
        if not model_pad.exists():
            raise RuntimeError(f"Modelversie '{versie}' mist {model_pad.name}.")
        model_bytes = _lees(model_pad, versleuteld)
        model = xgb.XGBRegressor()
        model.load_model(bytearray(model_bytes))
        modellen[kwantiel] = model

    historie_pad = doel / "historie.parquet"
    winkel_metadata_pad = doel / "winkel_metadata.parquet"
    metadata_pad = doel / "metadata.json"
    for verplicht_pad in (historie_pad, winkel_metadata_pad, metadata_pad):
        if not verplicht_pad.exists():
            raise RuntimeError(f"Modelversie '{versie}' mist {verplicht_pad.name}.")

    return {
        "modellen": modellen,
        "historie": pd.read_parquet(io.BytesIO(_lees(historie_pad, versleuteld))),
        "winkel_metadata": pd.read_parquet(io.BytesIO(_lees(winkel_metadata_pad, versleuteld))),
        "metadata": json.loads(_lees(metadata_pad, versleuteld).decode("utf-8")),
    }


def lijst_metadata_per_versie(basis_map: Path, versleuteld: bool = False) -> list[dict]:
    """Leest alleen metadata.json van elke modelversie onder basis_map — niet
    de modellen/historie zelf — voor een lichtgewicht overzicht van hoe de
    nauwkeurigheid zich over versies heeft ontwikkeld. Slaat een map zonder
    (leesbare) metadata.json stilzwijgend over: één onvolledige of corrupte
    versie mag het overzicht van de andere versies niet blokkeren. Chronologisch
    gesorteerd (oudste eerst) op aangemaakt_op, niet op mapnaam — een
    handmatig hernoemde of teller-gesuffixte map (zie schrijf_artefact) hoeft
    niet dezelfde volgorde te hebben als de mapnaam suggereert."""
    if not basis_map.exists():
        return []
    resultaten = []
    for map_pad in sorted(basis_map.iterdir()):
        if not map_pad.is_dir():
            continue
        metadata_pad = map_pad / "metadata.json"
        if not metadata_pad.exists():
            continue
        try:
            metadata = json.loads(_lees(metadata_pad, versleuteld).decode("utf-8"))
            resultaten.append({
                "versie": metadata["versie"],
                "aangemaakt_op": metadata["aangemaakt_op"],
                "rmspe": metadata["metrics"]["rmspe"],
                "coverage_p10_p90": metadata["metrics"]["coverage_p10_p90"],
            })
        except (json.JSONDecodeError, KeyError):
            continue
    resultaten.sort(key=lambda r: r["aangemaakt_op"])
    return resultaten
