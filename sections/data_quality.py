"""Tab 7 — Data & limits: what was cleaned, what can be trusted, and what cannot."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import charts, config, ui
from core.context import Context


def _pct(part: int, whole: int) -> str:
    return f"{part / whole:.2%}" if whole else "—"


def render(ctx: Context) -> None:
    st.header("7 · Data & limits: how far can we trust it?")
    report = ctx.report
    ui.key_message("the figures are solid for orders of magnitude and comparisons between sectors, but not for "
                   "proving causes or for fine differences between départements.")

    raw = report["rows_raw"]
    cols = st.columns(4)
    cols[0].metric("Rows in the file", ui.fmt_int(raw))
    cols[1].metric("Rows kept", ui.fmt_int(report["rows_kept"]), _pct(report["rows_kept"], raw), delta_color="off", delta_arrow="off")
    cols[2].metric("Invalid dates", ui.fmt_int(report["bad_dates"]), _pct(report["bad_dates"], raw), delta_color="off", delta_arrow="off")
    cols[3].metric("Duplicated ids", ui.fmt_int(report["duplicates"]), _pct(report["duplicates"], raw),
                   delta_color="off", delta_arrow="off")

    st.subheader("Validation checks")
    last_ok = ctx.last_complete_month == ctx.last_month
    checks = [
        ("All dates can be read", report["bad_dates"] == 0, f"{report['bad_dates']:,} rows removed"),
        ("No date before the platform launch (Nov 2018)", report["before_launch"] == 0,
         f"{report['before_launch']:,} rows removed"),
        ("No date in the future", report["future_dates"] == 0, f"{report['future_dates']:,} rows removed"),
        ("No duplicated report id", report["duplicates"] == 0, f"{report['duplicates']:,} removed (first kept)"),
        ("Sector always filled in", report["missing_category"] == 0,
         f"{report['missing_category']:,} kept as “Unspecified”"),
        ("Département usable (under 5% unlocated)",
         report["has_geo"] and report["unlocated"] / max(report["rows_kept"], 1) < 0.05,
         f"{report['unlocated']:,} rows without a recognised département"),
        ("Follow-up columns available", report["has_funnel"], "forwarded / read / answered"),
        ("Last month complete", last_ok, f"data ends {report['date_max']}"),
        ("All sector codes translated", not report["unmapped_categories"],
         f"{len(report['unmapped_categories'])} fall back to an automatic label"),
    ]
    st.dataframe(pd.DataFrame([{"Check": name, "Result": "✅ OK" if ok else "⚠️ Note", "Detail": detail}
                               for name, ok, detail in checks]), hide_index=True, width="stretch")

    left, right = st.columns(2)
    with left:
        missing = pd.DataFrame({"Field": list(report["missing_pct"]), "Missing (%)": list(report["missing_pct"].values())})
        missing["label"] = missing["Missing (%)"].map(lambda v: f"{v:.1f}%")
        fig = charts.hbar(missing, "Missing (%)", "Field", "Missing values by field (raw file)",
                          "Share of rows with no value (%)", "Field", text="label", height=380)
        st.plotly_chart(fig, width="stretch")
        ui.describe("horizontal bars of the share of empty values in each column used, before cleaning.")
    with right:
        st.markdown("**Columns used**")
        st.dataframe(pd.DataFrame({"Role": list(report["columns_detected"]),
                                   "Column in the file": list(report["columns_detected"].values())}),
                     hide_index=True, width="stretch")
        file = report["file"]
        st.caption(f"File {file['name']} ({file['size_mb']} MB), separator “{file['separator']}”.")

    _taxonomy(report)
    _limits()


def _taxonomy(report: dict) -> None:
    st.subheader("Did the sector list change over time?")
    taxonomy = pd.DataFrame(report["taxonomy"])
    first, last = pd.Timestamp(report["first_month"]), pd.Timestamp(report["last_complete_month"])
    partial = taxonomy[(pd.to_datetime(taxonomy["first_month"]) > first + pd.DateOffset(years=1))
                       | (pd.to_datetime(taxonomy["last_month"]) < last - pd.DateOffset(years=1))]
    st.markdown(
        f"**{len(partial)} of {len(taxonomy)} sectors** do not cover the whole period (they appear late or "
        "stop). A sector-by-sector comparison across years may therefore reflect a change of classification "
        "rather than a real change."
    )
    with st.expander("Active period of each sector"):
        st.dataframe(taxonomy.rename(columns={"category": "Sector", "first_month": "First month",
                                              "last_month": "Last month", "reports": "Reports"}),
                     hide_index=True, width="stretch")
    with st.expander("How source codes were translated"):
        table = pd.DataFrame(report["category_labels"]).rename(
            columns={"code": "Code in the file", "label": "English label", "mapped": "Translated in labels_en.csv"})
        st.dataframe(table, hide_index=True, width="stretch")
        st.caption("Codes marked False got an automatic word-by-word label; add them to "
                   "data/reference/labels_en.csv to fix the wording.")


def _limits() -> None:
    st.subheader("Assumptions, biases and limits")
    st.markdown(
        "- **A report is not proven fraud.** It is a claim made by a consumer, not checked here.\n"
        "- **Awareness bias.** The more people know the platform, the more reports it gets; a rise is not "
        "automatically more fraud.\n"
        "- **Profile bias.** People comfortable with digital tools report more; some groups are probably "
        "under-represented.\n"
        "- **Classification changes.** Sector names evolved; see the table above.\n"
        "- **Meaning of the département.** The file does not document whether it is the consumer's or the "
        "business's location; the pattern (Paris and inner suburbs far ahead) suggests the business. Per-capita "
        "rates should then be read as an indicator of where businesses are registered, not of consumer behaviour.\n"
        "- **Population and map.** Per-capita rates use rounded population figures (INSEE order of magnitude, "
        "around 2021); bubbles sit on approximate département centroids, not official boundaries.\n"
        "- **Reasons** are shown in the source's French wording, without accents or apostrophes.\n"
        "- **Follow-up flags** are empty before 2021 and only complete from 2022, so tab 5 uses reports filed "
        "since January 2022. Many reports (cold calls, for example) cannot be forwarded to an identified "
        "business, which lowers the sector reply rates.\n"
        "- **Seasonality** removes the growth trend (each month is compared with the surrounding 12-month "
        "average); sectors with under 3 years of history are skipped.\n"
        "- **No causality.** Nothing here shows that a factor *causes* more reports.\n"
        "- **Privacy.** Only aggregates (sector, month, département) are shown; no personal data and no "
        "company names."
    )
    st.caption(config.SOURCE_LINE)
