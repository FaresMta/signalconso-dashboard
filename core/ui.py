"""Formatting helpers and small Streamlit snippets used by every section."""
from __future__ import annotations

import streamlit as st

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December"]


def fmt_int(value: float) -> str:
    return f"{int(round(value)):,}"


def fmt_pct(value: float, digits: int = 0) -> str:
    return f"{value * 100:.{digits}f}%"


def shorten(text: str, width: int = 36) -> str:
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def key_message(text: str) -> None:
    """One-sentence takeaway shown at the top of each section (computed from the filtered data)."""
    st.markdown(f"**Key message —** {text}")


def describe(text: str) -> None:
    """Text alternative shown under a chart (accessibility)."""
    st.caption(f"Chart description: {text}")
