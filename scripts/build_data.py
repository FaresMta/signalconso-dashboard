"""Clean the raw CSV and write the small processed files used by the app (data/processed/).

Usage:  python scripts/build_data.py [path/to/file.csv]

It prints what was detected, what was removed, and which category codes still need an
English label in data/reference/labels_en.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import config, store  # noqa: E402


def main() -> int:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else config.raw_csv_path()
    if not csv_path.exists():
        print(f"File not found: {csv_path}\nRun  python scripts/download_data.py  first.")
        return 1

    print(f"Reading {csv_path} ...")
    data = store.build_processed(csv_path)
    report = data.report

    print("\nColumns detected")
    for role, column in report["columns_detected"].items():
        print(f"  {role:<14} <- {column}   ({report['missing_pct'][role]}% empty)")

    print("\nCleaning summary")
    for label, key in [("rows in file", "rows_raw"), ("rows kept", "rows_kept"), ("invalid dates", "bad_dates"),
                       ("before launch", "before_launch"), ("future dates", "future_dates"),
                       ("duplicated ids", "duplicates"), ("blank sector", "missing_category"),
                       ("no département", "unlocated")]:
        print(f"  {label:<16}{report[key]:>12,}")
    print(f"  period          {report['date_min']} -> {report['date_max']}")

    unmapped = report["unmapped_categories"]
    if unmapped:
        print(f"\n{len(unmapped)} category code(s) have no English label yet. Add them to "
              "data/reference/labels_en.csv (columns: field,code,label):")
        for code in unmapped:
            print(f"  category,{code},")
    else:
        print("\nAll category codes are translated.")

    print(f"\nProcessed files written to {config.processed_dir()}")
    print("Next:  streamlit run app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
