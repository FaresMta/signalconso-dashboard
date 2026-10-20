"""All the numbers shown in the dashboard. Pure pandas, no Streamlit.

Most functions take a `view`: the cube (see pipeline.py) filtered by the sidebar, with columns
ym, category, dept, region, n, forwarded, read, answered. `n` is the number of reports.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, geo

STAGES = ("n", "forwarded", "read", "answered")


# ------------------------------------------------------------------------------------------------
# Filters and calendar
# ------------------------------------------------------------------------------------------------
def filter_scope(cube: pd.DataFrame, categories, regions, include_overseas: bool) -> pd.DataFrame:
    """Keep the selected sectors / regions (an empty selection means "all")."""
    mask = pd.Series(True, index=cube.index)
    if categories:
        mask &= cube["category"].isin(categories)
    if regions:
        mask &= cube["region"].isin(regions)
    if not include_overseas:
        mask &= ~cube["dept"].isin(geo.OVERSEAS_CODES)
    return cube[mask]


def filter_period(cube: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return cube[(cube["ym"] >= start) & (cube["ym"] <= end)]


def complete_years(start, end, first_month, last_complete_month) -> list[int]:
    """Calendar years entirely covered by the selection AND by the data (January to December)."""
    low, high = max(start, first_month), min(end, last_complete_month)
    return [year for year in range(low.year, high.year + 1)
            if pd.Timestamp(year, 1, 1) >= low and pd.Timestamp(year, 12, 1) <= high]


def period_delta(base: pd.DataFrame, start, end, first_month, last_complete_month) -> float | None:
    """Change in reports versus the period of the same length just before (complete months only)."""
    end = min(end, last_complete_month)
    months = (end.year - start.year) * 12 + end.month - start.month + 1
    previous_start = start - pd.DateOffset(months=months)
    if months <= 0 or previous_start < first_month:
        return None
    current = base.loc[(base["ym"] >= start) & (base["ym"] <= end), "n"].sum()
    previous = base.loc[(base["ym"] >= previous_start) & (base["ym"] < start), "n"].sum()
    return float(current / previous - 1) if previous else None


# ------------------------------------------------------------------------------------------------
# Trend and sectors
# ------------------------------------------------------------------------------------------------
def monthly_totals(view: pd.DataFrame) -> pd.DataFrame:
    return view.groupby("ym", observed=True)["n"].sum().reset_index()


def monthly_by_sector(view: pd.DataFrame, sectors: list[str]) -> pd.DataFrame:
    sub = view[view["category"].isin(sectors)]
    out = sub.groupby(["ym", "category"], observed=True)["n"].sum().reset_index()
    out["category"] = out["category"].astype(str)
    return out


def sector_ranking(view: pd.DataFrame) -> pd.DataFrame:
    """Reports per sector with their share of the total, largest first."""
    out = view.groupby("category", observed=True)[list(STAGES)].sum().reset_index()
    out["category"] = out["category"].astype(str)
    out["share"] = out["n"] / out["n"].sum()
    return out.sort_values("n", ascending=False).reset_index(drop=True)


def yearly_totals(view: pd.DataFrame) -> pd.DataFrame:
    out = view.assign(year=view["ym"].dt.year).groupby("year")["n"].sum().reset_index()
    return out


def sector_movers(view: pd.DataFrame, year_a: int, year_b: int,
                  min_reports: int = config.MIN_REPORTS_FOR_RATES) -> pd.DataFrame:
    """Change in reports per sector between two complete years (sectors present in both)."""
    sub = view.assign(year=view["ym"].dt.year)
    sub = sub[sub["year"].isin([year_a, year_b])]
    table = (sub.groupby(["category", "year"], observed=True)["n"].sum()
             .unstack("year").reindex(columns=[year_a, year_b]).fillna(0))
    table = table[(table[year_a] >= min_reports) & (table[year_b] >= min_reports)].copy()
    table["change"] = table[year_b] / table[year_a] - 1
    table.index = table.index.astype(str)
    return table.rename_axis("sector").reset_index().sort_values("change", ascending=False)


# ------------------------------------------------------------------------------------------------
# Seasonality
# ------------------------------------------------------------------------------------------------
def _month_profile(series: pd.Series) -> pd.Series | None:
    """Typical month-of-year pattern of a monthly series, with the growth trend removed.

    Each month is divided by the centred 12-month moving average (so a steadily growing sector does not
    look "busier in December" just because December comes later in the year). The profile is the median
    ratio per calendar month, rescaled so that 1.0 = an average month.
    """
    series = series.sort_index()
    series = series[series.index >= series[series > 0].index.min()] if (series > 0).any() else series
    if len(series) < config.MIN_SEASON_MONTHS:
        return None
    series = series.asfreq("MS", fill_value=0).astype(float)
    weights = np.array([0.5] + [1.0] * 11 + [0.5]) / 12
    trend = series.rolling(13, center=True).apply(lambda window: float(window @ weights), raw=True)
    ratio = (series / trend).replace([np.inf, -np.inf], np.nan).dropna()
    profile = ratio.groupby(ratio.index.month).median().reindex(range(1, 13))
    if profile.isna().any():
        return None
    return profile / profile.mean()


def seasonality_index(view: pd.DataFrame, years: list[int], sectors: list[str]) -> pd.DataFrame:
    """Index by sector (rows) and month 1..12 (columns); 1.0 = an average month, growth trend removed.

    Uses complete calendar years only (up to December of the last one) and skips sectors with fewer
    than MIN_SEASON_MONTHS months of history.
    """
    if not years:
        return pd.DataFrame()
    end = pd.Timestamp(year=max(years), month=12, day=1)
    sub = view[(view["ym"] <= end) & view["category"].isin(sectors)]
    rows = {}
    for sector, part in sub.groupby("category", observed=True):
        profile = _month_profile(part.groupby("ym")["n"].sum())
        if profile is not None:
            rows[str(sector)] = profile
    return pd.DataFrame(rows).T if rows else pd.DataFrame()


def overall_seasonality(view: pd.DataFrame, years: list[int]) -> pd.Series | None:
    """Same profile for all selected sectors together (None if there is not enough history)."""
    if not years:
        return None
    end = pd.Timestamp(year=max(years), month=12, day=1)
    return _month_profile(view[view["ym"] <= end].groupby("ym")["n"].sum())


# ------------------------------------------------------------------------------------------------
# Départements
# ------------------------------------------------------------------------------------------------
def department_table(view: pd.DataFrame) -> pd.DataFrame:
    """One row per département: reports, reports per 100,000 residents, follow-up counts."""
    sums = view.groupby("dept", observed=True)[list(STAGES)].sum().reset_index()
    sums["dept"] = sums["dept"].astype(str)
    table = geo.departments().merge(sums, left_on="code", right_on="dept", how="left").drop(columns="dept")
    for column in STAGES:
        table[column] = table[column].fillna(0).astype(int)
    table["rate_100k"] = table["n"] / table["population_k"] * 100
    return table


def followup_only(view: pd.DataFrame) -> pd.DataFrame:
    """Reports filed from FOLLOWUP_START on, when the follow-up flags are reliable (all 0 before 2021).

    If the selection has nothing that recent, it is returned unchanged.
    """
    recent = view[view["ym"] >= pd.Timestamp(config.FOLLOWUP_START)]
    return recent if len(recent) else view


def department_profile(view: pd.DataFrame, code: str, top_sectors: int = 6) -> dict:
    """Facts for one département: volume, rank, reply rate and sector mix compared with France."""
    table = department_table(view)
    ranked = table[table["population_k"] > 0].sort_values("rate_100k", ascending=False).reset_index(drop=True)
    row = ranked[ranked["code"] == code].iloc[0]
    rank = int(ranked.index[ranked["code"] == code][0]) + 1

    local = view[view["dept"] == code]
    local_mix = local.groupby("category", observed=True)["n"].sum()
    france_mix = view.groupby("category", observed=True)["n"].sum()
    mix = pd.DataFrame({"local": local_mix / max(local_mix.sum(), 1),
                        "france": france_mix / max(france_mix.sum(), 1)}).fillna(0)
    mix = mix.sort_values("local", ascending=False).head(top_sectors)
    mix.index = mix.index.astype(str)

    recent = department_table(followup_only(view))
    local_recent = recent[recent["code"] == code]
    reply_rate_local = (float(local_recent["answered"].iloc[0] / local_recent["n"].iloc[0])
                        if len(local_recent) and local_recent["n"].iloc[0] else None)
    reply_rate_france = float(recent["answered"].sum() / recent["n"].sum()) if recent["n"].sum() else None

    return {
        "name": row["name"], "reports": int(row["n"]), "rate_100k": float(row["rate_100k"]),
        "rank": rank, "ranked": len(ranked),
        "reply_rate": reply_rate_local, "france_reply_rate": reply_rate_france,
        "mix": mix.reset_index(names="sector"),
    }


# ------------------------------------------------------------------------------------------------
# What happens after a report
# ------------------------------------------------------------------------------------------------
def funnel_counts(view: pd.DataFrame) -> dict[str, int]:
    """Counts at each stage, for reports filed since FOLLOWUP_START (see followup_only)."""
    totals = followup_only(view)[list(STAGES)].sum()
    return {stage: int(totals[stage]) for stage in STAGES}


def reply_by_sector(view: pd.DataFrame, min_reports: int = config.MIN_REPORTS_FOR_RATES) -> pd.DataFrame:
    out = sector_ranking(followup_only(view))
    out = out[out["n"] >= min_reports].copy()
    out["reply_rate"] = out["answered"] / out["n"]
    return out.sort_values("reply_rate", ascending=False).reset_index(drop=True)


def reply_by_year(view: pd.DataFrame) -> pd.DataFrame:
    out = view.assign(year=view["ym"].dt.year).groupby("year")[list(STAGES)].sum().reset_index()
    out["forwarded_rate"] = out["forwarded"] / out["n"]
    out["reply_rate"] = out["answered"] / out["n"]
    return out


def status_breakdown(statuses: pd.DataFrame, start, end, categories) -> pd.DataFrame:
    sub = statuses[(statuses["ym"] >= start) & (statuses["ym"] <= end)]
    if categories:
        sub = sub[sub["category"].isin(categories)]
    out = sub.groupby("status", as_index=False)["n"].sum().sort_values("n", ascending=False)
    out["share"] = out["n"] / out["n"].sum() if out["n"].sum() else 0.0
    return out.reset_index(drop=True)


def top_issues(issues: pd.DataFrame, start, end, sector: str, limit: int = 10) -> pd.DataFrame:
    sub = issues[(issues["ym"] >= start) & (issues["ym"] <= end) & (issues["category"] == sector)]
    return (sub.groupby("issue", as_index=False)["n"].sum()
            .sort_values("n", ascending=False).head(limit).reset_index(drop=True))


# ------------------------------------------------------------------------------------------------
# Extra 1: reply-gap what-if
# ------------------------------------------------------------------------------------------------
def observed_rates(counts: dict[str, int]) -> dict[str, float]:
    """Share forwarded (of filed), read (of forwarded) and answered (of read)."""
    def ratio(part, whole):
        return counts[part] / counts[whole] if counts[whole] else 0.0
    return {"forwarded": ratio("forwarded", "n"), "read": ratio("read", "forwarded"),
            "answered": ratio("answered", "read")}


def annual_volume(view: pd.DataFrame, last_complete_month: pd.Timestamp) -> float:
    """Reports per year at the current pace: the last 12 complete months of the selection."""
    monthly = monthly_totals(view[view["ym"] <= last_complete_month]).sort_values("ym").tail(12)
    return float(monthly["n"].sum() * 12 / len(monthly)) if len(monthly) else 0.0


def scenario_counts(volume: float, forwarded: float, read: float, answered: float) -> dict[str, float]:
    """Reports reaching each stage per year for the given conversion rates."""
    sent = volume * forwarded
    opened = sent * read
    return {"Filed": volume, "Forwarded": sent, "Read": opened, "Answered": opened * answered}
