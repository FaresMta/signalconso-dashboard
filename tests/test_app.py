"""End-to-end smoke tests: the whole app runs on the synthetic file and reacts to the widgets."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.fixtures import make_csv

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SC_RAW_CSV", str(make_csv(tmp_path / "signalconso.csv", n=8_000)))
    monkeypatch.setenv("SC_PROCESSED_DIR", str(tmp_path / "processed"))
    at = AppTest.from_file(APP, default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_renders_everything(app):
    assert len(app.tabs) == 8
    assert len(app.metric) >= 8
    assert len(app.get("plotly_chart")) >= 12
    titles = [h.value for h in app.main.header]
    assert titles[0].startswith("1 ·") and titles[-1].startswith("8 ·")


def test_all_text_is_english(app):
    text = " ".join(m.value for m in app.markdown) + " ".join(h.value for h in app.main.header)
    for french in ("Pourquoi", "Signalements", "Qualité", "Où ", "Conclusions"):
        assert french not in text


def test_sidebar_interactions(app):
    app.sidebar.select_slider[0].set_value(("2023-01", "2025-12")).run()
    assert not app.exception, [e.value for e in app.exception]
    app.sidebar.multiselect[0].select("Online purchase").run()
    assert not app.exception, [e.value for e in app.exception]
    app.sidebar.slider[0].set_value(5).run()
    app.sidebar.checkbox[0].uncheck().run()
    assert not app.exception, [e.value for e in app.exception]


def test_what_if_and_vigilance_widgets(app):
    sliders = [s for s in app.slider if s.label.startswith("Read")]
    assert sliders, "reply-gap sliders are missing"
    sliders[0].set_value(100).run()
    assert not app.exception, [e.value for e in app.exception]
    check = [s for s in app.selectbox if s.label == "Département"][0]
    check.select("33").run()
    assert not app.exception, [e.value for e in app.exception]


def test_empty_selection_is_handled(app):
    app.sidebar.select_slider[0].set_value(("2026-10", "2026-10")).run()
    app.sidebar.multiselect[1].select("Corse").run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.warning or app.info


def test_missing_data_shows_download_button(tmp_path, monkeypatch):
    monkeypatch.setenv("SC_RAW_CSV", str(tmp_path / "absent.csv"))
    monkeypatch.setenv("SC_PROCESSED_DIR", str(tmp_path / "none"))
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert [b.label for b in at.button] == ["⬇️ Download and prepare the data"]
