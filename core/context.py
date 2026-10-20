"""What every dashboard section receives: the data, the sidebar choices and the filtered views."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .pipeline import Datasets


@dataclass(frozen=True)
class Filters:
    start: pd.Timestamp
    end: pd.Timestamp
    categories: tuple[str, ...]      # empty = all sectors
    regions: tuple[str, ...]         # empty = all regions
    include_overseas: bool
    top_n: int


@dataclass
class Context:
    data: Datasets
    filters: Filters
    base: pd.DataFrame           # sector / region filters applied, all months
    view: pd.DataFrame           # all filters applied (this is what most charts use)
    period_view: pd.DataFrame    # period filter only (used by the "Your check" tab)
    first_month: pd.Timestamp
    last_month: pd.Timestamp
    last_complete_month: pd.Timestamp
    complete_years: list[int]

    @property
    def report(self) -> dict:
        return self.data.report

    @property
    def last_month_is_partial(self) -> bool:
        return self.last_complete_month < self.last_month
