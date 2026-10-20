"""Download the raw CSV, build the processed files, and load them.

Processed files (data/processed/) are small enough to commit, so a deployed app can start from them
without the 280 MB raw CSV. If the raw CSV is newer than the processed files, they are rebuilt.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests

from . import config
from .pipeline import Datasets, build_datasets

FILES = {"cube": "cube.parquet", "statuses": "statuses.parquet", "issues": "issues.parquet",
         "report": "report.json"}


def processed_paths() -> dict[str, Path]:
    folder = config.processed_dir()
    return {key: folder / name for key, name in FILES.items()}


def processed_available() -> bool:
    return all(path.exists() for path in processed_paths().values())


def raw_available() -> bool:
    return config.raw_csv_path().exists()


def data_available() -> bool:
    return processed_available() or raw_available()


def data_signature() -> str:
    """Changes whenever the data on disk changes (used as a cache key by the app)."""
    parts = []
    for path in [config.raw_csv_path(), *processed_paths().values()]:
        if path.exists():
            stat = path.stat()
            parts.append(f"{path}:{stat.st_size}:{int(stat.st_mtime)}")
    return "|".join(parts)


def download_raw(force: bool = False, timeout: int = 180) -> Path:
    """Download the CSV from data.gouv.fr into data/raw/ (skipped if already there)."""
    destination = config.raw_csv_path()
    if destination.exists() and not force:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(".part")
    headers = {"User-Agent": "EFREI-student-project/1.0 (data storytelling)"}
    with requests.get(config.RESOURCE_URL, stream=True, timeout=timeout, headers=headers) as response:
        response.raise_for_status()
        with open(partial, "wb") as handle:
            for block in response.iter_content(chunk_size=1 << 20):
                handle.write(block)
    partial.replace(destination)
    return destination


def build_processed(csv_path: Path | None = None) -> Datasets:
    """Read the raw CSV, aggregate it, and write the processed files."""
    data = build_datasets(csv_path or config.raw_csv_path())
    paths = processed_paths()
    paths["cube"].parent.mkdir(parents=True, exist_ok=True)
    data.cube.to_parquet(paths["cube"], index=False, compression="zstd")
    data.statuses.to_parquet(paths["statuses"], index=False, compression="zstd")
    data.issues.to_parquet(paths["issues"], index=False, compression="zstd")
    paths["report"].write_text(json.dumps(data.report, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def _read_processed() -> Datasets:
    paths = processed_paths()
    return Datasets(
        cube=pd.read_parquet(paths["cube"]),
        statuses=pd.read_parquet(paths["statuses"]),
        issues=pd.read_parquet(paths["issues"]),
        report=json.loads(paths["report"].read_text(encoding="utf-8")),
    )


def _is_stale() -> bool:
    """True when the raw CSV exists and is newer than the processed files."""
    if not raw_available():
        return False
    newest_raw = config.raw_csv_path().stat().st_mtime
    oldest_processed = min(path.stat().st_mtime for path in processed_paths().values())
    return newest_raw > oldest_processed


def load_datasets() -> Datasets:
    if processed_available() and not _is_stale():
        return _read_processed()
    if raw_available():
        return build_processed()
    raise FileNotFoundError(
        f"No data found. Run `python scripts/download_data.py` then `python scripts/build_data.py` "
        f"(raw CSV expected at {config.raw_csv_path()})."
    )
