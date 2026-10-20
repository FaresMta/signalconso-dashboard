"""Tab 4 — Where: départements compared per head of population."""
from __future__ import annotations

import streamlit as st

from core import charts, metrics, ui
from core.context import Context


def render(ctx: Context) -> None:
    st.header("4 · Where are reports concentrated?")
    if not ctx.report["has_geo"]:
        st.warning("The file has no département column, so geographic views are unavailable.")
        return

    st.warning(
        "**Read with care.** The file does not say whether the département is where the *consumer* lives or "
        "where the *reported business* is based. The very high rates in Paris and its inner suburbs "
        "(Hauts-de-Seine, Val-de-Marne, Seine-Saint-Denis) look like head-office locations, so this tab may "
        "show where businesses are registered rather than where consumers are. Confirm with the publisher "
        "(DGCCRF) before drawing conclusions about residents.", icon="⚠️")
    table = metrics.department_table(ctx.view)
    if table["n"].sum() == 0:
        st.warning("No located report in the current selection.")
        return

    choice = st.radio("Measure", ["Per 100,000 residents", "Number of reports"], horizontal=True,
                      help="The per-capita rate removes the effect of département size.")
    metric = "rate_100k" if choice.startswith("Per") else "n"
    top = table.sort_values(metric, ascending=False).iloc[0]
    median = table["rate_100k"].median()
    if metric == "rate_100k":
        ratio = f", **{top['rate_100k'] / median:.1f}×** the median département ({median:.0f})" if median else ""
        ui.key_message(f"**{top['name']}** has the highest rate, **{top['rate_100k']:.0f} reports per "
                       f"100,000 residents**{ratio}. Ranking by raw count would mostly rank population.")
    else:
        ui.key_message(f"**{top['name']}** has the most reports (**{ui.fmt_int(top['n'])}**), but large "
                       "départements dominate raw counts: switch to the per-capita rate to compare fairly.")

    mainland = table[~table["is_overseas"]]
    st.plotly_chart(charts.bubble_map(mainland, metric, choice, f"Mainland France — {choice.lower()}"),
                    width="stretch")
    ui.describe(f"map of mainland France with one bubble per département; size and colour show "
                f"“{choice.lower()}”. Overseas départements appear in the rankings below.")

    left, right = st.columns(2)
    with left:
        n = ctx.filters.top_n
        ranked = table.sort_values(metric, ascending=False).head(n).copy()
        ranked["label"] = ranked["name"] + " (" + ranked["code"] + ")"
        fig = charts.hbar(ranked, metric, "label", f"Top {n} départements", choice, "Département",
                          hover=["n", "rate_100k"])
        st.plotly_chart(fig, width="stretch")
        ui.describe(f"horizontal bars of the {n} départements with the highest “{choice.lower()}”.")
    with right:
        st.plotly_chart(charts.histogram(table["rate_100k"], median, "How unequal are départements?",
                                         "Reports per 100,000 residents"), width="stretch")
        p10, p90 = table["rate_100k"].quantile(0.1), table["rate_100k"].quantile(0.9)
        spread = f" The 90th percentile is about {p90 / p10:.1f}× the 10th." if p10 > 0 else ""
        ui.describe(f"histogram of départements by reports per 100,000 residents; median {median:.0f}.{spread}")

    with st.expander("All départements (table)"):
        show = table.sort_values("rate_100k", ascending=False)[
            ["code", "name", "region", "n", "population_k", "rate_100k"]].rename(columns={
                "code": "Code", "name": "Département", "region": "Region", "n": "Reports",
                "population_k": "Population (thousands)", "rate_100k": "Per 100,000 residents"})
        st.dataframe(show.round(1), hide_index=True, width="stretch")
    st.caption("Per-capita rates use rounded population figures and bubbles sit on approximate centroids "
               "(see “Data & limits”). Differences between départements also reflect reporting habits.")
