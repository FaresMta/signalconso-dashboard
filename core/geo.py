"""Geographic reference: French départements, regions, population and map positions.

The table lives in data/reference/departments.csv (code, name, region, lat, lon, population_k).
Population figures are rounded orders of magnitude (INSEE, around 2021) and the coordinates are
approximate centroids: good for a bubble map and per-capita comparisons, not for official statistics.
"""
from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from . import config
from .text import ascii_key

UNLOCATED = "UNK"
OVERSEAS_CODES = ("971", "972", "973", "974", "976")
_CODE_PATTERN = re.compile(r"^(2[AB]|\d{1,3})$")


@lru_cache(maxsize=1)
def departments() -> pd.DataFrame:
    table = pd.read_csv(config.REFERENCE_DIR / "departments.csv", dtype={"code": str})
    table["is_overseas"] = table["code"].isin(OVERSEAS_CODES)
    return table


@lru_cache(maxsize=1)
def _codes() -> frozenset[str]:
    return frozenset(departments()["code"])


@lru_cache(maxsize=1)
def _name_to_code() -> dict[str, str]:
    table = departments()
    return {ascii_key(name): code for code, name in zip(table["code"], table["name"])}


@lru_cache(maxsize=1)
def region_by_code() -> dict[str, str]:
    table = departments()
    return dict(zip(table["code"], table["region"]))


def normalize_code(value: object) -> str | None:
    """"75", "2a", "02", "2", "75.0" -> a valid département code, or None."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().upper()
    if text.endswith(".0"):
        text = text[:-2]
    if not _CODE_PATTERN.match(text):
        return None
    if text.isdigit() and len(text) == 1:
        text = text.zfill(2)
    return text if text in _codes() else None


def code_from_name(value: object) -> str | None:
    """"Val-d'Oise" -> "95"."""
    if value is None or pd.isna(value):
        return None
    return _name_to_code().get(ascii_key(value))
