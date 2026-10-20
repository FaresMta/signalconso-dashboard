"""Tab 2 — What: volume over time, which sectors dominate, and a drill-down into one sector."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import charts, metrics, ui
from core.context import Context


def render(ctx: Context) -> None:
    st.header("2 · The big picture: what is reported?")
    view, top_n = ctx.view, ctx.filters.top_n
    ranking = metrics.sector_ranking(view)
    top = ranking.iloc[0]
    ui.key_message(
        f"**{ui.fmt_int(view['n'].sum())} reports** in the selection; **{ui.fmt_pct(top['share'])}** concern "
        f"“{top['category']}” and the top 3 sectors together make up "
        f"**{ui.fmt_pct(ranking.head(3)['share'].sum())}**."
    )

    left, right = st.columns([3, 2])
    with left:
        mode = st.radio("Trend view", ["All sectors", "Top 5 sectors"], horizontal=True)
        if mode == "All sectors":
            data = metrics.monthly_totals(view)
            fig = charts.trend(data[data["ym"] <= ctx.last_complete_month], "Reports per month")
            alt = "monthly number of reports, all selected sectors together"
        else:
            top5 = ranking["category"].head(5).tolist()
            data = metrics.monthly_by_sector(view, top5)
            data["category"] = data["category"].map(lambda s: ui.shorten(s, 32))
            fig = charts.trend(data[data["ym"] <= ctx.last_complete_month], "Reports per month, top 5 sectors",
                               color="category")
            alt = "monthly number of reports for the five sectors with most reports"
        st.plotly_chart(fig, width="stretch")
        ui.describe(f"line chart of the {alt}. The dotted vertical line marks the first COVID-19 lockdown.")
        if ctx.last_month_is_partial:
            st.caption(f"{ctx.last_month:%B %Y} is still in progress and is left out of the trend.")
    with right:
        shown = ranking.head(top_n).copy()
        shown["sector"] = shown["category"].map(lambda s: ui.shorten(s, 34))
        shown["share_pct"] = (shown["share"] * 100).round(1)
        shown["label"] = shown["n"].map(ui.fmt_int)
        fig = charts.hbar(shown, "n", "sector", f"Top {top_n} sectors", "Reports (number)", "Sector",
                          text="label", hover=["share_pct"])
        fig.update_traces(hovertemplate="%{y}<br>%{x:,} reports (%{customdata[0]}%)<extra></extra>")
        st.plotly_chart(fig, width="stretch")
        ui.describe(f"horizontal bars of the {top_n} sectors with the most reports; the longest bar is "
                    f"“{top['category']}” with {ui.fmt_int(top['n'])} reports.")

    _before_after(ctx)
    st.divider()
    _sector_drilldown(ctx, ranking)


def _before_after(ctx: Context) -> None:
    st.subheader("Before and after: is it growing?")
    yearly = metrics.yearly_totals(ctx.view)
    partial = ctx.last_month.year if ctx.last_month_is_partial else None
    years = ctx.complete_years
    left, right = st.columns([2, 3])
    with left:
        st.plotly_chart(charts.yearly_bars(yearly, partial, "Reports per year"), width="stretch")
        ui.describe("bars of reports per filing year; the current year, if incomplete, is shown in grey.")
    with right:
        if len(years) < 2:
            st.info("Select a period covering at least two full calendar years to compare years.")
            return
        year_a, year_b = years[-2], years[-1]
        totals = yearly.set_index("year")["n"]
        change = totals[year_b] / totals[year_a] - 1
        st.markdown(
            f"Between **{year_a}** and **{year_b}** (full years) reports changed by **{change:+.0%}** "
            f"({ui.fmt_int(totals[year_a])} → {ui.fmt_int(totals[year_b])}). A rise can mean more problems "
            "**or** a better-known platform; these data cannot tell the two apart."
        )
        movers = metrics.sector_movers(ctx.view, year_a, year_b)
        if movers.empty:
            return
        movers["sector"] = movers["sector"].map(lambda s: ui.shorten(s, 40))
        movers["change"] = movers["change"].map(lambda v: f"{v:+.0%}")
        for year in (year_a, year_b):
            movers[year] = movers[year].map(ui.fmt_int)
        table = movers.rename(columns={year_a: str(year_a), year_b: str(year_b), "sector": "Sector",
                                       "change": "Change"})
        st.markdown(f"**Biggest movers, {year_a} → {year_b}** (sectors with at least 1,000 reports each year)")
        st.dataframe(pd.concat([table.head(3), table.tail(3)]), hide_index=True, width="stretch")
        st.caption("Sector names changed over time (see “Data & limits”): a sector appearing or disappearing "
                   "may reflect a new classification rather than a real change.")


def _sector_drilldown(ctx: Context, ranking: pd.DataFrame) -> None:
    st.subheader("Drill into a sector")
    sector = st.selectbox("Sector", ranking["category"].tolist(), help="Sorted by number of reports.")
    row = ranking[ranking["category"] == sector].iloc[0]
    st.markdown(f"“{sector}”: **{ui.fmt_int(row['n'])} reports**, **{ui.fmt_pct(row['share'])}** of the selection.")
    left, right = st.columns(2)
    with left:
        data = metrics.monthly_by_sector(ctx.view, [sector])
        data = data[data["ym"] <= ctx.last_complete_month]
        st.plotly_chart(charts.trend(data, f"“{ui.shorten(sector, 40)}” per month", height=380), width="stretch")
        ui.describe("monthly number of reports for the chosen sector.")
    with right:
        issues = metrics.top_issues(ctx.data.issues, ctx.filters.start, ctx.filters.end, sector)
        if issues.empty:
            st.info("No detailed reasons recorded for this sector in the selected period.")
            return
        issues["reason"] = issues["issue"].map(lambda s: ui.shorten(s, 60))
        fig = charts.hbar(issues, "n", "reason", "Most cited specific reasons", "Reports (number)",
                          "Reason (original French wording)", height=380, hover=["issue"])
        st.plotly_chart(fig, width="stretch")
        ui.describe("horizontal bars of the most cited specific reasons for this sector. Reasons are shown in "
                    "the source's French wording (the file has no translation).")
