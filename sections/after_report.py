"""Tab 5 — Then what? The follow-up funnel, plus the reply-gap what-if (extra 1)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import charts, config, metrics, ui
from core.context import Context


def render(ctx: Context) -> None:
    st.header("5 · What happens after a report?")
    if not ctx.report["has_funnel"]:
        st.info("The follow-up columns (forwarded / read / answered) are not in the file.")
        return

    if ctx.view["ym"].min() < pd.Timestamp(config.FOLLOWUP_START):
        st.info("Follow-up flags (forwarded, read, answered) are all empty before 2021 and still ramping up "
                "in 2021, so the funnel and rates below use reports filed from **January 2022**. The yearly "
                "line chart shows the whole history.")
    counts = metrics.funnel_counts(ctx.view)
    rates = metrics.observed_rates(counts)
    total = counts["n"]
    ui.key_message(
        f"of {ui.fmt_int(total)} reports, **{ui.fmt_pct(rates['forwarded'])}** are forwarded to the business; "
        f"**{ui.fmt_pct(rates['read'])}** of those are read and **{ui.fmt_pct(rates['answered'])}** of the "
        f"read ones get an answer — so only **{ui.fmt_pct(counts['answered'] / total)}** of all reports "
        "end with a reply."
    )

    stages = [("Filed", counts["n"]), ("Forwarded to the business", counts["forwarded"]),
              ("Read by the business", counts["read"]), ("Answered", counts["answered"])]
    st.plotly_chart(charts.funnel(stages, "From filing to a reply"), width="stretch")
    ui.describe("funnel with four stages (filed, forwarded, read, answered), each showing its count and its "
                "share of filed reports.")

    left, right = st.columns(2)
    with left:
        by_sector = metrics.reply_by_sector(ctx.view).head(ctx.filters.top_n * 2)
        if by_sector.empty:
            st.info("No sector has enough reports in this selection to compare reply rates.")
        else:
            by_sector = by_sector.assign(
                sector=by_sector["category"].map(lambda s: ui.shorten(s, 34)),
                pct=(by_sector["reply_rate"] * 100).round(1),
                label=(by_sector["reply_rate"] * 100).round(0).astype(int).astype(str) + "%")
            fig = charts.hbar(by_sector, "pct", "sector", "Share of reports that got an answer, by sector",
                              "Reports answered (% of filed)", "Sector", text="label", hover=["n"], height=520)
            st.plotly_chart(fig, width="stretch")
            ui.describe("horizontal bars of the reply rate for sectors with at least 1,000 reports; "
                        "sectors differ widely in how often businesses answer.")
    with right:
        st.plotly_chart(charts.rate_lines(metrics.reply_by_year(ctx.view),
                                          "Follow-up by year of filing"), width="stretch")
        ui.describe("two lines by filing year: share of reports forwarded to the business and share answered. "
                    "Before 2021 the flags are empty, which explains the zeros; the latest year is slightly lower because "
                    "businesses have had less time to respond.")

    _what_if(ctx, counts, rates)
    _statuses(ctx)


def _what_if(ctx: Context, counts: dict[str, int], rates: dict[str, float]) -> None:
    st.divider()
    st.subheader("Extra · What if more reports got an answer?")
    st.write(
        "Move the sliders to set a target for each step. The simulator applies those rates to the "
        "**current yearly volume** and shows how many more reports would end with a reply."
    )
    volume = metrics.annual_volume(ctx.view, ctx.last_complete_month)
    st.caption(f"Assumption: about **{ui.fmt_int(volume)} reports per year** (the last 12 complete months "
               "of the current selection, extrapolated), and each step's rate applies equally to every report.")

    cols = st.columns(3)
    targets = {}
    for col, (key, label) in zip(cols, [("forwarded", "Filed → forwarded"), ("read", "Forwarded → read"),
                                         ("answered", "Read → answered")]):
        default = int(round(rates[key] * 100))
        with col:
            chosen = st.slider(f"{label} (%)", 0, 100, default, key=f"whatif_{key}_{default}")
        # A slider left at its starting value keeps the exact observed rate (no rounding noise).
        targets[key] = rates[key] if chosen == default else chosen / 100

    now = metrics.scenario_counts(volume, rates["forwarded"], rates["read"], rates["answered"])
    scenario = metrics.scenario_counts(volume, targets["forwarded"], targets["read"], targets["answered"])
    extra = scenario["Answered"] - now["Answered"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Answered per year today", ui.fmt_int(now["Answered"]))
    m2.metric("Answered per year in the scenario", ui.fmt_int(scenario["Answered"]),
              f"{extra:+,.0f}", delta_color="normal")
    m3.metric("Share of filed reports answered", ui.fmt_pct(scenario["Answered"] / volume) if volume else "—",
              f"{(scenario['Answered'] - now['Answered']) / volume * 100:+.1f} pts" if volume else None)

    data = pd.DataFrame([{"Stage": stage, "Scenario": label, "Reports per year": value}
                         for label, source in (("Today", now), ("Scenario", scenario))
                         for stage, value in source.items()])
    st.plotly_chart(charts.grouped_bars(data, "Stage", "Reports per year", "Scenario",
                                        "Reports reaching each stage, per year", "Stage", "Reports per year"),
                    width="stretch")
    ui.describe("grouped bars comparing today with the scenario at each stage of the funnel.")
    st.caption("This is a simple what-if, not a forecast: it assumes the volume stays constant and ignores "
               "whether a reply actually resolves the problem.")


def _statuses(ctx: Context) -> None:
    if not ctx.report["has_status"]:
        return
    statuses = metrics.status_breakdown(ctx.data.statuses, ctx.filters.start, ctx.filters.end,
                                        ctx.filters.categories)
    if statuses.empty:
        return
    with st.expander("How businesses handled reports (platform status)"):
        statuses = statuses.assign(pct=(statuses["share"] * 100).round(1))
        fig = charts.hbar(statuses, "n", "status", "Reports by platform status", "Reports (number)", "Status",
                          hover=["pct"], height=380)
        st.plotly_chart(fig, width="stretch")
        ui.describe("horizontal bars of reports by the status given by the platform.")
        st.caption("Status labels are translated from the platform's codes; check the official definitions "
                   "before quoting them. This chart follows the period and sector filters but not the region filter.")
