"""Turn the raw SignalConso CSV (~2 million rows) into three small tables plus a quality report.

The CSV is read in chunks and aggregated on the fly, so memory stays low and the result is tiny:

    cube      one row per (month, sector, département) with report counts and follow-up counts
    statuses  one row per (month, sector, status)
    issues    one row per (month, sector, specific issue)

Cleaning rules (all counted in the report, nothing is dropped silently):
    - unparsable dates, dates before the platform launch, dates in the future -> row removed
    - duplicated `id` (first occurrence kept)                                  -> row removed
    - missing category        -> kept, labelled "Unspecified"
    - unknown département     -> kept, counted as "unlocated" (excluded from maps and per-capita rates)
"""
from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, geo, labels, schema

TRUTHY = {"1", "true", "t", "yes", "oui", "vrai"}
FOLLOW_UP = ("forwarded", "read", "answered")


@dataclass
class Datasets:
    cube: pd.DataFrame
    statuses: pd.DataFrame
    issues: pd.DataFrame
    report: dict


# ------------------------------------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------------------------------------
def read_header(path: Path) -> tuple[str, list[str]]:
    """Return (separator, column names) from the first line of the CSV."""
    with open(path, encoding="utf-8-sig", errors="replace") as handle:
        first_line = handle.readline()
    separator = max(";,\t|", key=first_line.count)
    header = next(csv.reader([first_line], delimiter=separator))
    return separator, [name.strip() for name in header]


def map_unique(series: pd.Series, func) -> pd.Series:
    """Apply `func` once per distinct value (fast on millions of rows). Missing values give None."""
    cat = series if isinstance(series.dtype, pd.CategoricalDtype) else series.astype("category")
    lookup = np.array([func(value) for value in cat.cat.categories] + [None], dtype=object)
    return pd.Series(lookup[cat.cat.codes.to_numpy()], index=series.index, dtype=object)


def parse_dates(series: pd.Series) -> pd.Series:
    """ISO dates -> naive timestamps in Paris time; anything unparsable becomes NaT."""
    parsed = pd.to_datetime(series, errors="coerce", utc=True, format="ISO8601")
    return parsed.dt.tz_convert("Europe/Paris").dt.tz_localize(None)


def to_flag(series: pd.Series) -> pd.Series:
    """0/1 follow-up columns -> int64."""
    flags = map_unique(series, lambda value: int(str(value).strip().lower() in TRUTHY))
    return flags.fillna(0).astype("int64")


def _month_start(dates: pd.Series) -> pd.Series:
    return dates.dt.to_period("M").dt.to_timestamp()


# ------------------------------------------------------------------------------------------------
# One chunk
# ------------------------------------------------------------------------------------------------
def _process_chunk(chunk: pd.DataFrame, cols: dict[str, str], state: dict) -> dict[str, pd.DataFrame]:
    stats: Counter = state["stats"]
    stats["rows_raw"] += len(chunk)
    for field, column in cols.items():
        state["missing"][field] += int(chunk[column].isna().sum())

    # 1. dates
    dates = parse_dates(chunk[cols["date"]])
    launch = pd.Timestamp(config.LAUNCH_DATE)
    stats["bad_dates"] += int(dates.isna().sum())
    stats["before_launch"] += int((dates < launch).sum())
    stats["future_dates"] += int((dates >= state["tomorrow"]).sum())
    keep = dates.notna() & (dates >= launch) & (dates < state["tomorrow"])

    # 2. duplicated ids (hashes keep memory small: 2 M ids = 16 MB)
    if "id" in cols:
        ids = chunk[cols["id"]]
        valid = ids.notna().to_numpy()
        hashes = pd.util.hash_array(np.asarray(ids.fillna(""), dtype=object))
        duplicated = valid & (pd.Series(hashes).duplicated().to_numpy() | np.isin(hashes, state["seen_ids"]))
        state["seen_ids"] = np.concatenate([state["seen_ids"], hashes[valid]])
        stats["duplicates"] += int(duplicated.sum())
        keep = keep & ~duplicated

    stats["rows_kept"] += int(keep.sum())
    if not keep.any():
        return {}
    rows = chunk.loc[keep]
    dates = dates[keep]
    state["date_min"] = min(filter(None, [state["date_min"], dates.min()]))
    state["date_max"] = max(filter(None, [state["date_max"], dates.max()]))
    month = _month_start(dates)

    # 3. sector (category)
    code = rows[cols["category"]].str.strip()
    code = code.where(code != "")
    stats["missing_category"] += int(code.isna().sum())
    state["category_codes"].update(code.dropna().unique())
    sector = map_unique(code, labels.category_label).fillna(labels.UNSPECIFIED)

    # 4. département
    dept = pd.Series(None, index=rows.index, dtype=object)
    if "dep_code" in cols:
        dept = map_unique(rows[cols["dep_code"]], geo.normalize_code)
    if "dep_name" in cols:
        dept = dept.where(dept.notna(), map_unique(rows[cols["dep_name"]], geo.code_from_name))
    stats["unlocated"] += int(dept.isna().sum())
    dept = dept.fillna(geo.UNLOCATED)

    # 5. main aggregate
    frame = pd.DataFrame({"ym": month, "category": sector, "dept": dept, "n": 1})
    for stage in FOLLOW_UP:
        frame[stage] = to_flag(rows[cols[stage]]) if stage in cols else 0
    parts = {"cube": frame.groupby(["ym", "category", "dept"], as_index=False, sort=False).sum()}

    # 6. optional aggregates
    if "status" in cols:
        status = map_unique(rows[cols["status"]], labels.status_label).fillna(labels.UNKNOWN_STATUS)
        small = pd.DataFrame({"ym": month, "category": sector, "status": status})
        parts["statuses"] = small.groupby(["ym", "category", "status"], sort=False).size().rename("n").reset_index()
    if "subcategories" in cols:
        issue = map_unique(rows[cols["subcategories"]], labels.issue_text)
        small = pd.DataFrame({"ym": month, "category": sector, "issue": issue})[issue.notna()]
        parts["issues"] = small.groupby(["ym", "category", "issue"], sort=False).size().rename("n").reset_index()
    return parts


# ------------------------------------------------------------------------------------------------
# Whole file
# ------------------------------------------------------------------------------------------------
def build_datasets(csv_path: Path, chunk_rows: int = config.CHUNK_ROWS) -> Datasets:
    separator, header = read_header(csv_path)
    cols = schema.detect_columns(header)

    state = {
        "stats": Counter(), "missing": Counter(), "seen_ids": np.array([], dtype="uint64"),
        "category_codes": set(), "date_min": None, "date_max": None,
        "tomorrow": pd.Timestamp.now().normalize() + pd.Timedelta(days=1),
    }
    collected: dict[str, list[pd.DataFrame]] = {"cube": [], "statuses": [], "issues": []}

    reader = pd.read_csv(
        csv_path, sep=separator, usecols=sorted(set(cols.values())), dtype=str,
        encoding="utf-8-sig", encoding_errors="replace", chunksize=chunk_rows,
    )
    for chunk in reader:
        for name, part in _process_chunk(chunk, cols, state).items():
            collected[name].append(part)
    if not collected["cube"]:
        raise ValueError("No valid row found: check the date column and the file format.")

    cube = _finish_cube(pd.concat(collected["cube"]))
    statuses = _finish_small(collected["statuses"], ["ym", "category", "status"])
    issues = _finish_small(collected["issues"], ["ym", "category", "issue"])
    report = _build_report(csv_path, separator, header, cols, state, cube)
    return Datasets(cube, statuses, issues, report)


def _finish_cube(parts: pd.DataFrame) -> pd.DataFrame:
    cube = parts.groupby(["ym", "category", "dept"], as_index=False).sum()
    cube["region"] = cube["dept"].map(geo.region_by_code()).fillna("Unlocated")
    for column in ("category", "dept", "region"):
        cube[column] = cube[column].astype("category")
    for column in ("n", *FOLLOW_UP):
        cube[column] = cube[column].astype("int32")
    return cube.sort_values(["ym", "category", "dept"]).reset_index(drop=True)


def _finish_small(parts: list[pd.DataFrame], keys: list[str]) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame(columns=[*keys, "n"])
    table = pd.concat(parts).groupby(keys, as_index=False)["n"].sum()
    table["category"] = table["category"].astype("category")
    table["n"] = table["n"].astype("int32")
    return table


def _build_report(csv_path, separator, header, cols, state, cube) -> dict:
    stats, rows_raw = state["stats"], state["stats"]["rows_raw"]
    date_max = state["date_max"]
    last_complete = date_max.to_period("M").to_timestamp()
    if (date_max + pd.Timedelta(days=1)).month == date_max.month:  # the last month is still running
        last_complete -= pd.DateOffset(months=1)

    category_labels = []
    for code in sorted(state["category_codes"]):
        label, mapped = labels.lookup("category", code)
        category_labels.append({"code": code, "label": label, "mapped": mapped})

    span = cube.groupby("category", observed=True).agg(
        first_month=("ym", "min"), last_month=("ym", "max"), reports=("n", "sum")).reset_index()
    taxonomy = [
        {"category": str(row.category), "first_month": str(row.first_month.date()),
         "last_month": str(row.last_month.date()), "reports": int(row.reports)}
        for row in span.sort_values("reports", ascending=False).itertuples()
    ]
    return {
        "source": {"title": config.DATASET_TITLE, "page": config.DATASET_PAGE, "license": config.LICENSE},
        "file": {"name": csv_path.name, "size_mb": round(csv_path.stat().st_size / 1e6, 1),
                 "separator": separator, "columns": header},
        "columns_detected": cols,
        "rows_raw": int(rows_raw),
        "rows_kept": int(stats["rows_kept"]),
        "rows_removed": int(rows_raw - stats["rows_kept"]),
        "bad_dates": int(stats["bad_dates"]),
        "before_launch": int(stats["before_launch"]),
        "future_dates": int(stats["future_dates"]),
        "duplicates": int(stats["duplicates"]),
        "missing_category": int(stats["missing_category"]),
        "unlocated": int(stats["unlocated"]),
        "date_min": str(state["date_min"].date()),
        "date_max": str(date_max.date()),
        "first_month": str(cube["ym"].min().date()),
        "last_complete_month": str(last_complete.date()),
        "missing_pct": {f: round(100 * state["missing"][f] / max(rows_raw, 1), 2) for f in cols},
        "has_geo": "dep_code" in cols or "dep_name" in cols,
        "has_funnel": all(stage in cols for stage in FOLLOW_UP),
        "has_status": "status" in cols,
        "has_issues": "subcategories" in cols,
        "category_labels": category_labels,
        "unmapped_categories": [c["code"] for c in category_labels if not c["mapped"]],
        "taxonomy": taxonomy,
    }
