"""SignalConso — data-storytelling dashboard (EFREI Paris, #EFREIDataStories2026).

Run with:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import config, metrics, store, ui
from core.context import Context, Filters
from core.pipeline import Datasets
from sections import after_report, big_picture, data_quality, intro, takeaways, vigilance, when, where

st.set_page_config(page_title="SignalConso — consumer reports", page_icon="🛡️", layout="wide")

TABS = [
    ("1 · Context", intro), ("2 · What", big_picture), ("3 · When", when), ("4 · Where", where),
    ("5 · Then what?", after_report), ("6 · Your check", vigilance), ("7 · Data & limits", data_quality),
    ("8 · Takeaways", takeaways),
]


@st.cache_resource(show_spinner="Loading the data…")
def get_datasets(signature: str) -> Datasets:
    """Loaded once per data version. `signature` changes when files on disk change."""
    return store.load_datasets()


def ensure_data() -> Datasets:
    if not store.data_available():
        st.title("🛡️ SignalConso — consumer reports")
        st.warning("The data file is not on this machine yet. It is public (data.gouv.fr, Open Licence) and "
                   "about 280 MB; preparing it takes under a minute.")
        if st.button("⬇️ Download and prepare the data", type="primary"):
            with st.spinner("Downloading…"):
                try:
                    store.download_raw()
                except Exception as error:  # network, permissions…
                    st.error(f"Download failed: {error}. Alternative: `python scripts/download_data.py`.")
                    st.stop()
            st.rerun()
        st.stop()
    try:
        return get_datasets(store.data_signature())
    except Exception as error:
        st.error(f"Could not prepare the data: {error}")
        st.stop()


def sidebar(data: Datasets) -> Filters:
    report, cube = data.report, data.cube
    first, last = pd.Timestamp(report["first_month"]), pd.Timestamp(report["date_max"]).to_period("M").to_timestamp()
    months = [m.strftime("%Y-%m") for m in pd.date_range(first, last, freq="MS")]
    sectors = cube.groupby("category", observed=True)["n"].sum().sort_values(ascending=False).index.astype(str).tolist()
    regions = sorted(r for r in cube["region"].astype(str).unique())

    with st.sidebar:
        st.header("Filters")
        start, end = st.select_slider("Period (months)", options=months, value=(months[0], months[-1]),
                                      format_func=lambda m: pd.Timestamp(m).strftime("%b %Y"))
        categories = st.multiselect("Sectors", sectors, placeholder="All sectors",
                                    help="Leave empty to keep every sector.")
        selected_regions = st.multiselect("Regions", regions, placeholder="All regions",
                                          help="Leave empty to keep every region.")
        overseas = st.checkbox("Include overseas départements", value=True)
        st.header("Display")
        top_n = st.slider("Items in rankings", 5, 15, 10)
        st.divider()
        st.caption(config.SOURCE_LINE)
    return Filters(pd.Timestamp(start), pd.Timestamp(end), tuple(categories), tuple(selected_regions),
                   overseas, top_n)


def build_context(data: Datasets, filters: Filters) -> Context:
    report = data.report
    first = pd.Timestamp(report["first_month"])
    last = pd.Timestamp(report["date_max"]).to_period("M").to_timestamp()
    last_complete = pd.Timestamp(report["last_complete_month"])
    base = metrics.filter_scope(data.cube, filters.categories, filters.regions, filters.include_overseas)
    return Context(
        data=data, filters=filters, base=base,
        view=metrics.filter_period(base, filters.start, filters.end),
        period_view=metrics.filter_period(data.cube, filters.start, filters.end),
        first_month=first, last_month=last, last_complete_month=last_complete,
        complete_years=metrics.complete_years(filters.start, filters.end, first, last_complete),
    )


def kpis(ctx: Context) -> None:
    view, report = ctx.view, ctx.report
    total = int(view["n"].sum())
    delta = metrics.period_delta(ctx.base, ctx.filters.start, ctx.filters.end, ctx.first_month,
                                 ctx.last_complete_month)
    top = metrics.sector_ranking(view).iloc[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Reports in the selection", ui.fmt_int(total),
                f"{delta:+.0%} vs previous period" if delta is not None else None, delta_color="inverse",
                help="Compared with the period of the same length just before (complete months only).")
    col2.metric("Top sector", ui.shorten(top["category"], 28), f"{ui.fmt_pct(top['share'])} of reports",
                delta_color="off", delta_arrow="off", help=top["category"])
    if report["has_funnel"]:
        col3.metric("Reports answered by the business", ui.fmt_pct(answered_share(view)),
                    help="Share of filed reports that received a reply from the business.")
    if report["has_geo"]:
        table = metrics.department_table(view)
        if table["n"].sum() > 0:
            best = table.sort_values("rate_100k", ascending=False).iloc[0]
            col4.metric("Top département (business location)", best["name"], f"{best['rate_100k']:.0f} per 100,000 residents",
                        delta_color="off", delta_arrow="off")


def answered_share(view: pd.DataFrame) -> float:
    counts = metrics.funnel_counts(view)
    return counts["answered"] / counts["n"] if counts["n"] else 0.0


def main() -> None:
    data = ensure_data()
    filters = sidebar(data)
    if filters.start > filters.end:
        st.warning("The start month is after the end month.")
        st.stop()
    ctx = build_context(data, filters)
    if ctx.view.empty:
        st.title("🛡️ SignalConso — consumer reports")
        st.warning("No report matches these filters. Widen the period or clear a filter.")
        st.stop()

    st.title("🛡️ SignalConso: what do consumers report, when, where — and who answers?")
    st.caption(config.SOURCE_LINE)
    kpis(ctx)
    for tab, (_, module) in zip(st.tabs([name for name, _ in TABS]), TABS):
        with tab:
            module.render(ctx)


main()
