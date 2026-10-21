"""Tab 1 — Hook, context, audience and the questions the story answers."""
from __future__ import annotations

import streamlit as st

from core import config, ui
from core.context import Context


def render(ctx: Context) -> None:
    st.header("1 · Why this dashboard?")
    cube, report = ctx.data.cube, ctx.report

    yearly = cube.assign(year=cube["ym"].dt.year).groupby("year")["n"].sum()
    full_years = [y for y in yearly.index if ctx.first_month.year < y <= ctx.last_complete_month.year - 1
                  or (y == ctx.last_complete_month.year and ctx.last_complete_month.month == 12)]
    per_day = f" — about **{ui.fmt_int(yearly[full_years[-1]] / 365)} per day** in {full_years[-1]}" if full_years else ""
    st.markdown(
        f"> **{ui.fmt_int(report['rows_kept'])} consumer reports** were filed on SignalConso between "
        f"**{report['date_min']}** and **{report['date_max']}**{per_day}. Each one is a person who "
        "ordered something that never arrived, was cold-called, or could not cancel a subscription."
    )

    left, right = st.columns(2)
    with left:
        st.subheader("The problem")
        st.write(
            "When something goes wrong with a purchase, it is hard to know whether it is common, which "
            "sectors are known for it, when to be extra careful, and whether reporting leads anywhere. "
            "Aggregating the reports answers those questions without exposing anyone: no personal data "
            "and no company names are used here."
        )
        st.subheader("Who is it for?")
        st.markdown(
            "- **Consumers, students included:** know where problems concentrate and when to be careful.\n"
            "- **Consumer associations and mediators:** target prevention and follow-up.\n"
            "- **Public authorities:** spot sectors, seasons and territories to watch."
        )
    with right:
        st.subheader("Four questions, four steps")
        st.markdown(
            "1. **What?** Which sectors draw the most reports, and is the volume rising?\n"
            "2. **When?** Are there seasons when a sector peaks?\n"
            "3. **Where?** In which départements are the reported businesses based, per head of population?\n"
            "4. **Then what?** Do reports reach the business, get read, get an answer — and what if "
            "more of them did? *(extra: reply-gap simulator)*"
        )
        st.subheader("Plus a tool for you")
        st.write(
            "**Your check** lets you pick a département and a sector to see how the businesses based there "
            "compare with the rest of France. *(extra: vigilance check)*"
        )

    with st.expander("Definitions"):
        st.markdown(
            "- **Report:** one declaration filed by a consumer on SignalConso. It is a claim, not a proven fraud.\n"
            "- **Sector:** the category chosen by the consumer when filing.\n"
            "- **Forwarded / read / answered:** the three follow-up flags in the file — the report was "
            "sent to the business, the business opened it, the business replied. The same three stages "
            "appear on the authority's own public dashboard.\n"
            "- **Département:** most likely where the reported business is based (see “Where”).\n"
            "- **Per 100,000 residents:** reports divided by the département's population, so large "
            "départements do not dominate by size alone."
        )

    st.info(
        "**Keep in mind:** reports depend on how well known the platform is, and on who uses it. "
        "Read the numbers as orders of magnitude, not as a measure of fraud. See “Data & limits”.",
        icon="⚠️",
    )
    st.caption(
        f"Data: [{config.DATASET_TITLE}]({config.DATASET_PAGE}), {config.PUBLISHER}, "
        f"under the {config.LICENSE}."
    )
