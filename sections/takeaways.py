"""Tab 8 — Takeaways: insights, implications and next steps."""
from __future__ import annotations

import streamlit as st

from core import metrics, ui
from core.context import Context


def render(ctx: Context) -> None:
    st.header("8 · What we learn, and what to do")
    view, report = ctx.view, ctx.report
    ranking = metrics.sector_ranking(view)
    top3 = ", ".join(f"“{row.category}” ({ui.fmt_pct(row.share)})" for row in ranking.head(3).itertuples())
    insights = [f"**Concentration.** Three sectors dominate the selection: {top3}."]

    if ctx.complete_years:
        profile = metrics.overall_seasonality(view, ctx.complete_years)
        if profile is not None:
            insights.append(
                f"**Timing.** Once the growth trend is removed, reports peak in "
                f"**{ui.MONTHS_FULL[int(profile.idxmax()) - 1]}** ({profile.max():.2f}× an average month) and are "
                f"lowest in **{ui.MONTHS_FULL[int(profile.idxmin()) - 1]}** ({profile.min():.2f}×).")

    if report["has_geo"]:
        table = metrics.department_table(view)
        if table["n"].sum() > 0:
            top = table.sort_values("rate_100k", ascending=False).iloc[0]
            insights.append(f"**Territory.** Businesses based in {top['name']} draw the most reports per resident "
                            f"({top['rate_100k']:.0f} per 100,000): a head-office effect rather than a map of "
                            "where consumers live.")

    if report["has_funnel"]:
        counts = metrics.funnel_counts(view)
        rates = metrics.observed_rates(counts)
        steps = {"filed → forwarded": rates["forwarded"], "forwarded → read": rates["read"],
                 "read → answered": rates["answered"]}
        weakest = min(steps, key=steps.get)
        insights.append(f"**Follow-up.** {ui.fmt_pct(counts['answered'] / counts['n'])} of reports filed since "
                        f"2022 end with a business reply; the weakest step is “{weakest}” "
                        f"({ui.fmt_pct(steps[weakest])} get through).")
    st.success("\n\n".join(f"- {text}" for text in insights))

    left, right = st.columns(2)
    with left:
        st.subheader("Implications")
        st.markdown(
            "**For consumers**\n"
            "- Be most careful in the sectors and months that stand out above.\n"
            "- Keep proof, contact the business first, then report.\n\n"
            "**For prevention and consumer bodies**\n"
            "- Schedule campaigns *before* the seasonal peaks, not after.\n"
            "- Focus on the sectors with many reports and few replies.\n\n"
            "**For the platform and regulators**\n"
            "- The weakest step of the chain (see Follow-up above) is where a reminder or a better contact route "
            "could pay off: use the simulator in tab 5 to size it."
        )
    with right:
        st.subheader("Next steps")
        st.markdown(
            "- Replace the embedded population figures with the official INSEE legal population.\n"
            "- Use official département boundaries for a shaded (choropleth) map.\n"
            "- Group the specific reasons into themes with simple text analysis.\n"
            "- Compare with another public source, such as product recalls (RappelConso) or hygiene inspections.\n"
            "- Check whether sectors with low reply rates are also those with more “unfounded” statuses."
        )

    st.divider()
    export = ranking.rename(columns={"category": "sector", "n": "reports", "forwarded": "forwarded_to_business",
                                     "read": "read_by_business", "answered": "answered_by_business"})
    st.download_button("⬇️ Download the sector ranking (CSV)", export.to_csv(index=False).encode("utf-8"),
                       file_name="signalconso_sector_ranking.csv", mime="text/csv",
                       help="Aggregated counts for the current filters; no individual records.")
    st.caption("This work describes declared reports. It does not prove causes and does not single out any company.")
