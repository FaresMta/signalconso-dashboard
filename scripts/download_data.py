"""Download the SignalConso CSV from data.gouv.fr into data/raw/.

Usage:  python scripts/download_data.py [--force]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import config, store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="download again even if the file exists")
    args = parser.parse_args()

    destination = config.raw_csv_path()
    if destination.exists() and not args.force:
        print(f"Already there: {destination} ({destination.stat().st_size / 1e6:.0f} MB). Use --force to replace it.")
        return 0

    print(f"Downloading from {config.RESOURCE_URL}\n(several hundred MB, this can take a few minutes)")
    try:
        path = store.download_raw(force=args.force)
    except Exception as error:  # network problems are the common failure
        print(f"\nDownload failed: {error}\n"
              f"Download the CSV manually from {config.DATASET_PAGE}\nand save it as {destination}")
        return 1
    print(f"Saved {path} ({path.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
