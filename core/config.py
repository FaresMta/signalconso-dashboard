"""Project-wide constants: dataset identity, file locations and thresholds.

Paths can be overridden with environment variables (used by the tests):
    SC_RAW_CSV         path of the raw CSV
    SC_PROCESSED_DIR   folder holding the processed files
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- Dataset identity (data.gouv.fr, approved portal) -------------------------------------------
DATASET_TITLE = "SignalConso"
DATASET_PAGE = "https://www.data.gouv.fr/datasets/signalconso"
RESOURCE_URL = "https://www.data.gouv.fr/api/1/datasets/r/106add51-e925-4121-b0e4-81489c26a43f"
PUBLISHER = "DGCCRF, French Ministries of Economy and Finance"
LICENSE = "Licence Ouverte / Open Licence (Etalab)"
SOURCE_LINE = f"Source: {DATASET_TITLE} — {PUBLISHER} — data.gouv.fr — {LICENSE}"

# --- Locations -----------------------------------------------------------------------------------
REFERENCE_DIR = ROOT / "data" / "reference"


def raw_csv_path() -> Path:
    return Path(os.environ.get("SC_RAW_CSV", ROOT / "data" / "raw" / "signalconso.csv"))


def processed_dir() -> Path:
    return Path(os.environ.get("SC_PROCESSED_DIR", ROOT / "data" / "processed"))


# --- Cleaning rules ------------------------------------------------------------------------------
LAUNCH_DATE = "2018-11-01"   # the dataset starts on 2018-11-24; anything earlier is an error
CHUNK_ROWS = 250_000         # rows read at a time when building the processed files

# --- Analysis thresholds -------------------------------------------------------------------------
MIN_SEASON_MONTHS = 36       # a sector needs >= 36 consecutive months to get a seasonal profile
FOLLOWUP_START = "2022-01-01"  # forwarded/read/answered flags are all 0 before 2021 and ramp up in 2021
MIN_REPORTS_FOR_RATES = 1_000  # sectors below this volume are left out of rate rankings
