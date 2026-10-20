"""Tab 3 — When: seasonality by sector."""
from __future__ import annotations

import streamlit as st

from core import charts, metrics, ui
from core.context import Context


def render(ctx: Context) -> None:
    st.header("3 · When are people most affected?")
    years = ctx.complete_years
    if not years:
        st.info("Seasonality needs at least one full calendar year (January to December). "
                "Widen the period in the sidebar.")
        return

    ranking = metrics.sector_ranking(ctx.view)
    sectors = ranking["category"].head(ctx.filters.top_n).tolist()
    index = metrics.seasonality_index(ctx.view, years, sectors)
    overall = metrics.overall_seasonality(ctx.view, years)
    if index.empty or overall is None:
        st.info("Not enough monthly data in this selection to compute a seasonal profile.")
        return

    flat = index.stack()
    (best_sector, best_month), best_value = flat.idxmax(), flat.max()
    ui.key_message(
        f"the sharpest seasonal peak is “{best_sector}” in **{ui.MONTHS_FULL[int(best_month) - 1]}**, at "
        f"**{best_value:.1f}×** an average month for that sector. Across all selected sectors the busiest "
        f"month is **{ui.MONTHS_FULL[int(overall.idxmax()) - 1]}** ({overall.max():.2f}×)."
    )

    left, right = st.columns([3, 2])
    with left:
        st.plotly_chart(charts.heatmap(index, "Seasonal index by sector"), width="stretch")
        ui.describe("heatmap with sectors in rows and months in columns; darker cells are months with more "
                    "reports than that sector's average month.")
    with right:
        choice = st.selectbox("Sector profile", ["All selected sectors", *index.index.tolist()])
        profile = overall if choice == "All selected sectors" else index.loc[choice]
        st.plotly_chart(charts.month_bars(profile, f"Monthly profile: {ui.shorten(choice, 34)}"),
                        width="stretch")
        peak = int(profile.idxmax())
        ui.describe(f"bars of the monthly index for {choice}; the highest bar is {ui.MONTHS_FULL[peak - 1]} "
                    f"({profile.max():.2f}× an average month); the dashed line is the average month.")

    st.caption(
        f"How to read it: each month is compared with the 12-month average around it, so the steady growth of "
        f"reports does not create a fake end-of-year peak; the profile is the median over the years "
        f"(up to {years[-1]}). Sectors with fewer than 3 years of history are left out. Seasonality is "
        f"descriptive: it shows *when* reports are filed, not why."
    )
