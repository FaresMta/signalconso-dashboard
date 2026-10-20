"""Numbers shown in the dashboard, checked against the cube."""
import pandas as pd
import pytest

from core import metrics
from core.pipeline import build_datasets
from tests.fixtures import make_csv


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    return build_datasets(make_csv(tmp_path_factory.mktemp("raw") / "signalconso.csv", n=15_000), chunk_rows=4_000)


@pytest.fixture(scope="module")
def cube(data):
    return data.cube


def test_filters(cube):
    sector = str(cube["category"].iloc[0])
    only = metrics.filter_scope(cube, (sector,), (), True)
    assert set(only["category"].astype(str)) == {sector}
    assert metrics.filter_scope(cube, (), (), True).shape == cube.shape
    no_overseas = metrics.filter_scope(cube, (), (), False)
    assert "974" not in set(no_overseas["dept"].astype(str))
    start, end = pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-01")
    year = metrics.filter_period(cube, start, end)
    assert year["ym"].min() >= start and year["ym"].max() <= end


def test_complete_years():
    first, last = pd.Timestamp("2018-11-01"), pd.Timestamp("2026-09-01")
    assert metrics.complete_years(first, pd.Timestamp("2026-10-01"), first, last) == list(range(2019, 2026))
    assert metrics.complete_years(pd.Timestamp("2021-03-01"), pd.Timestamp("2023-12-01"), first, last) == [2022, 2023]
    assert metrics.complete_years(pd.Timestamp("2025-02-01"), pd.Timestamp("2025-11-01"), first, last) == []


def test_ranking_shares_sum_to_one(cube):
    ranking = metrics.sector_ranking(cube)
    assert ranking["n"].sum() == cube["n"].sum()
    assert ranking["share"].sum() == pytest.approx(1)
    assert ranking["n"].is_monotonic_decreasing


def test_seasonality_mean_is_one(cube):
    years = list(range(2019, 2026))
    sectors = metrics.sector_ranking(cube)["category"].head(5).tolist()
    index = metrics.seasonality_index(cube, years, sectors)
    assert index.shape[1] == 12 and not index.empty
    assert index.mean(axis=1).round(6).eq(1).all()
    overall = metrics.overall_seasonality(cube, years)
    assert overall.mean() == pytest.approx(1)
    assert overall.idxmax() == 12          # the fixture boosts December


def test_department_table_and_profile(cube):
    table = metrics.department_table(cube)
    assert len(table) == 101
    paris = table[table["code"] == "75"].iloc[0]
    assert paris["rate_100k"] == pytest.approx(paris["n"] / paris["population_k"] * 100)
    profile = metrics.department_profile(cube, "75")
    assert profile["reports"] == int(paris["n"]) and 1 <= profile["rank"] <= profile["ranked"]
    assert profile["mix"]["local"].sum() <= 1 + 1e-9


def test_funnel_and_scenario(cube):
    counts = metrics.funnel_counts(cube)
    assert counts["n"] >= counts["forwarded"] >= counts["read"] >= counts["answered"] > 0
    rates = metrics.observed_rates(counts)
    now = metrics.scenario_counts(1000, **rates)
    assert now["Answered"] == pytest.approx(1000 * counts["answered"] / counts["n"])
    better = metrics.scenario_counts(1000, 1.0, 1.0, 1.0)
    assert better == {"Filed": 1000, "Forwarded": 1000, "Read": 1000, "Answered": 1000}
    assert metrics.observed_rates({"n": 0, "forwarded": 0, "read": 0, "answered": 0})["answered"] == 0


def test_reply_tables(cube):
    by_sector = metrics.reply_by_sector(cube, min_reports=500)
    assert by_sector["reply_rate"].between(0, 1).all() and by_sector["reply_rate"].is_monotonic_decreasing
    by_year = metrics.reply_by_year(cube)
    assert (by_year["reply_rate"] <= by_year["forwarded_rate"]).all()


def test_period_delta(cube):
    first, last = pd.Timestamp("2019-01-01"), pd.Timestamp("2026-09-01")
    assert metrics.period_delta(cube, pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-01"), first, last) is not None
    assert metrics.period_delta(cube, first, pd.Timestamp("2019-12-01"), first, last) is None   # nothing before


def test_movers_and_issues(cube, data):
    movers = metrics.sector_movers(cube, 2024, 2025, min_reports=10)
    assert {"sector", "change"} <= set(movers.columns)
    sector = metrics.sector_ranking(cube)["category"].iloc[0]
    issues = metrics.top_issues(data.issues, pd.Timestamp("2019-01-01"), pd.Timestamp("2026-10-01"), sector)
    assert len(issues) > 0 and issues["n"].is_monotonic_decreasing
