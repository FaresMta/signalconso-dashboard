"""Plotly figures. One consistent style: colour-blind-safe palette, titled axes with units."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from . import ui

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#555555"]  # Okabe-Ito
HIGHLIGHT, MUTED = "#D55E00", "#9AA5B1"
EVENTS = [(pd.Timestamp("2020-03-17"), "First COVID-19 lockdown")]


def _style(fig: go.Figure, title: str, x_title: str | None = None, y_title: str | None = None,
           height: int = 420, legend_title: str | None = None) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=60, b=10),
        title=dict(text=title, x=0, xanchor="left", font=dict(size=17)),
        font=dict(size=14, color="#1b1b1b"), legend_title_text=legend_title, hoverlabel=dict(font_size=13),
    )
    if x_title is not None:
        fig.update_xaxes(title_text=x_title)
    if y_title is not None:
        fig.update_yaxes(title_text=y_title)
    return fig


def trend(data: pd.DataFrame, title: str, color: str | None = None, height: int = 440) -> go.Figure:
    """Monthly line chart (columns ym, n[, color]) with the COVID-19 lockdown marked."""
    fig = px.line(data, x="ym", y="n", color=color, color_discrete_sequence=PALETTE)
    hover = "%{x|%b %Y}<br>%{y:,} reports<extra>%{fullData.name}</extra>" if color else \
            "%{x|%b %Y}<br>%{y:,} reports<extra></extra>"
    fig.update_traces(hovertemplate=hover)
    if len(data):
        for when, text in EVENTS:
            if data["ym"].min() <= when <= data["ym"].max():
                fig.add_shape(type="line", x0=when, x1=when, y0=0, y1=1, yref="paper",
                              line=dict(color="#555555", dash="dot", width=1.5))
                fig.add_annotation(x=when, y=1, yref="paper", text=text, showarrow=False,
                                   xanchor="left", yanchor="top", font=dict(size=12))
    return _style(fig, title, "Month", "Reports per month", height, "Sector")


def hbar(data: pd.DataFrame, x: str, y: str, title: str, x_title: str, y_title: str,
         text: str | None = None, hover: list[str] | None = None, height: int = 440,
         color: str = PALETTE[0]) -> go.Figure:
    """Horizontal bars, largest on top."""
    fig = px.bar(data, x=x, y=y, orientation="h", text=text, hover_data=hover, color_discrete_sequence=[color])
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_traces(textposition="outside", cliponaxis=False)
    if len(data):
        fig.update_xaxes(range=[0, float(data[x].max()) * 1.5])     # room for the value labels
    return _style(fig, title, x_title, y_title, height)


def yearly_bars(data: pd.DataFrame, partial_year: int | None, title: str) -> go.Figure:
    """Reports per year; the incomplete year (if any) is drawn in a different colour."""
    data = data.copy()
    data["status"] = ["Incomplete year" if year == partial_year else "Complete year" for year in data["year"]]
    fig = px.bar(data, x="year", y="n", color="status", text="n",
                 color_discrete_map={"Complete year": PALETTE[0], "Incomplete year": MUTED})
    fig.update_traces(texttemplate="%{y:.3s}", textposition="outside", cliponaxis=False, textfont_size=12,
                      constraintext="none")
    fig.update_yaxes(range=[0, float(data["n"].max()) * 1.15])
    fig.update_xaxes(dtick=1)
    return _style(fig, title, "Year", "Reports per year", 400, "")


def heatmap(index: pd.DataFrame, title: str, height: int = 520) -> go.Figure:
    """Seasonality index: sectors x months, 1.0 = an average month."""
    fig = go.Figure(go.Heatmap(
        z=index.values, x=ui.MONTHS, y=[ui.shorten(s, 38) for s in index.index], colorscale="Blues", zmin=0,
        colorbar=dict(title="Index<br>(1 = average<br>month)"),
        hovertemplate="%{y}<br>%{x}: %{z:.2f}× an average month<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return _style(fig, title, "Month of the year", "Sector", height)


def month_bars(profile: pd.Series, title: str) -> go.Figure:
    """Seasonality profile of one sector: bars per month, dashed line at 1.0."""
    data = pd.DataFrame({"Month": ui.MONTHS, "index": profile.to_numpy()})
    data["highlight"] = data["index"] == data["index"].max()
    fig = px.bar(data, x="Month", y="index", color="highlight",
                 color_discrete_map={True: HIGHLIGHT, False: PALETTE[0]})
    fig.update_traces(hovertemplate="%{x}: %{y:.2f}× an average month<extra></extra>")
    fig.add_hline(y=1, line_dash="dash", line_color="#333333", annotation_text="Average month",
                  annotation_position="top left")
    fig.update_layout(showlegend=False)
    return _style(fig, title, "Month of the year", "Index (1 = average month)", 380)


def bubble_map(table: pd.DataFrame, metric: str, metric_title: str, title: str) -> go.Figure:
    data = table.copy()
    data["size_value"] = data[metric].clip(lower=0) + 1e-9
    fig = px.scatter_map(
        data, lat="lat", lon="lon", size="size_value", color=metric, hover_name="name",
        hover_data={"region": True, "n": ":,", "rate_100k": ":.0f", "lat": False, "lon": False,
                    "size_value": False, metric: False},
        color_continuous_scale="YlOrRd", range_color=(0, float(data[metric].quantile(0.95)) or None), size_max=34, zoom=4.7, center=dict(lat=46.6, lon=2.5),
        map_style="carto-positron", labels={"n": "Reports", "rate_100k": "Per 100,000 residents",
                                            "region": "Region"})
    fig.update_layout(coloraxis_colorbar=dict(title=metric_title))
    return _style(fig, title, None, None, 560)


def histogram(values: pd.Series, median: float, title: str, x_title: str) -> go.Figure:
    fig = px.histogram(values, nbins=20, color_discrete_sequence=[PALETTE[0]])
    fig.update_traces(hovertemplate="%{x}<br>%{y} départements<extra></extra>")
    fig.add_vline(x=median, line_dash="dash", line_color=HIGHLIGHT,
                  annotation_text=f"Median: {median:.0f}", annotation_position="top right")
    fig.update_layout(showlegend=False)
    return _style(fig, title, x_title, "Number of départements", 380)


def funnel(stages: list[tuple[str, float]], title: str) -> go.Figure:
    fig = go.Figure(go.Funnel(
        y=[name for name, _ in stages], x=[value for _, value in stages],
        texttemplate="%{value:,.0f}<br>%{percentInitial:.0%}", textposition="inside",
        marker=dict(color=PALETTE[: len(stages)]),
        hovertemplate="%{y}<br>%{x:,.0f} reports<br>%{percentInitial:.1%} of filed reports<extra></extra>"))
    return _style(fig, title, None, None, 380)


def grouped_bars(data: pd.DataFrame, x: str, y: str, color: str, title: str, x_title: str, y_title: str,
                 height: int = 420) -> go.Figure:
    fig = px.bar(data, x=x, y=y, color=color, barmode="group", color_discrete_sequence=PALETTE)
    return _style(fig, title, x_title, y_title, height, "")


def rate_lines(data: pd.DataFrame, title: str) -> go.Figure:
    """Share of filed reports forwarded / answered, by filing year."""
    long = data.melt(id_vars="year", value_vars=["forwarded_rate", "reply_rate"], var_name="stage",
                     value_name="rate")
    long["stage"] = long["stage"].map({"forwarded_rate": "Forwarded to the business",
                                       "reply_rate": "Answered by the business"})
    long["rate"] = long["rate"] * 100
    fig = px.line(long, x="year", y="rate", color="stage", markers=True, color_discrete_sequence=PALETTE)
    fig.update_xaxes(dtick=1)
    fig.update_traces(hovertemplate="%{x}: %{y:.0f}%<extra>%{fullData.name}</extra>")
    return _style(fig, title, "Year the report was filed", "Share of filed reports (%)", 400, "")
