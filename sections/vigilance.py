"""Tab 6 — Your check (extra 2): how does my département and sector compare with France?

Uses the sidebar period only: the sector and département are chosen here.
"""
from __future__ import annotations

import streamlit as st

from core import charts, geo, metrics, ui
from core.context import Context


def render(ctx: Context) -> None:
    st.header("6 · Your check")
    st.write("Pick a département and, if you like, a sector. The département is most likely where the reported "
             "*business* is based (see tab 4). Everything below uses the period chosen in the sidebar and "
             "compares your choice with the whole of France.")
    if not ctx.report["has_geo"]:
        st.warning("The file has no département column, so this check is unavailable.")
        return

    departments = geo.departments().sort_values("name")
    options = departments["code"].tolist()
    labels = dict(zip(departments["code"], departments["name"] + " (" + departments["code"] + ")"))
    ranking = metrics.sector_ranking(ctx.period_view)

    c1, c2 = st.columns(2)
    code = c1.selectbox("Département", options, index=options.index("75") if "75" in options else 0,
                        format_func=labels.get)
    sector = c2.selectbox("Sector", ["All sectors", *ranking["category"].tolist()])

    scope = ctx.period_view if sector == "All sectors" else ctx.period_view[ctx.period_view["category"] == sector]
    if scope["n"].sum() == 0:
        st.info("No report for this choice in the selected period.")
        return
    profile = metrics.department_profile(scope, code)
    if profile["reports"] == 0:
        st.info(f"No report located in {profile['name']} for this choice in the selected period.")
        return

    where = f"“{sector}” reports" if sector != "All sectors" else "reports"
    ui.key_message(
        f"Businesses based in {profile['name']} have **{ui.fmt_int(profile['reports'])} {where}** in the period, "
        f"**{profile['rate_100k']:.0f} per 100,000 residents**: rank **{profile['rank']} of "
        f"{profile['ranked']}** départements (1 = most reports per resident)."
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Reports", ui.fmt_int(profile["reports"]))
    m2.metric("Per 100,000 residents", f"{profile['rate_100k']:.0f}")
    m3.metric("Rank (per capita)", f"{profile['rank']} / {profile['ranked']}")
    if profile["reply_rate"] is not None and profile["france_reply_rate"] is not None:
        gap = (profile["reply_rate"] - profile["france_reply_rate"]) * 100
        m4.metric("Reports answered", ui.fmt_pct(profile["reply_rate"]), f"{gap:+.1f} pts vs France",
                  delta_color="normal")

    left, right = st.columns(2)
    with left:
        if sector == "All sectors":
            mix = profile["mix"].copy()
            mix["sector"] = mix["sector"].map(lambda s: ui.shorten(s, 30))
            long = mix.melt(id_vars="sector", value_vars=["local", "france"], var_name="Where", value_name="share")
            long["Where"] = long["Where"].map({"local": profile["name"], "france": "France"})
            long["share"] = long["share"] * 100
            st.plotly_chart(charts.grouped_bars(long, "sector", "share", "Where",
                                                f"Sector mix: {profile['name']} vs France", "Sector",
                                                "Share of reports (%)"), width="stretch")
            ui.describe(f"grouped bars comparing the share of each top sector in {profile['name']} with its "
                        "share in France; a taller local bar means that sector is over-represented here.")
        else:
            local = scope[scope["dept"] == code]
            months = metrics.monthly_totals(local)
            months = months[months["ym"] <= ctx.last_complete_month]
            st.plotly_chart(charts.trend(months, f"“{ui.shorten(sector, 30)}” in {profile['name']}", height=380),
                            width="stretch")
            ui.describe(f"monthly number of {sector} reports in {profile['name']}.")
    with right:
        years = ctx.complete_years
        index = metrics.overall_seasonality(scope, years) if years else None
        if index is None:
            st.info("Select a period covering a full calendar year to see when to be most careful.")
        else:
            title = "When to be most careful" + ("" if sector == "All sectors" else f": {ui.shorten(sector, 28)}")
            st.plotly_chart(charts.month_bars(index, title), width="stretch")
            ui.describe(f"bars of the national monthly index; busiest month: "
                        f"{ui.MONTHS_FULL[int(index.idxmax()) - 1]}. This profile is national, not local.")

    st.subheader("What to do")
    st.markdown(
        "- **Keep proof:** order confirmations, emails, screenshots, call dates.\n"
        "- **Contact the business first** in writing, then **file a report on SignalConso** if it does not help.\n"
        "- **Be extra careful** in the peak months shown above and in the sectors that are over-represented here.\n"
        "- **Never pay or share bank details** to someone who contacts you without being asked."
    )
    st.caption("A report is a claim, not proven fraud. Small départements can show large swings with few reports. "
               "The département is most likely the business's, not the consumer's (see tab 4).")
