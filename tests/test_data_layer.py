"""Schema detection, labels, geography and the chunked pipeline."""
import pandas as pd
import pytest

from core import geo, labels
from core.pipeline import build_datasets, map_unique, read_header
from core.schema import SchemaError, detect_columns
from tests.fixtures import HEADER, make_csv

N_VALID_ROWS = 20_000


@pytest.fixture(scope="module")
def datasets(tmp_path_factory):
    path = make_csv(tmp_path_factory.mktemp("raw") / "signalconso.csv", n=N_VALID_ROWS)
    return build_datasets(path, chunk_rows=3_000)   # small chunks: exercises duplicates across chunks


# --- schema ---------------------------------------------------------------------------------------
def test_detect_real_header():
    found = detect_columns(HEADER)
    assert found["date"] == "Date" and found["category"] == "category"
    assert found["forwarded"] == "Signalement Transmis"
    assert found["read"] == "Signalement Lu par l'entreprise"
    assert found["answered"] == "Signalement ayant reçu une réponse"
    assert found["dep_code"] == "dep_code" and found["dep_name"] == "dep_name"


def test_detect_is_tolerant_and_strict_on_required():
    assert detect_columns(["ID", "CATEGORY", "date"])["date"] == "date"
    with pytest.raises(SchemaError):
        detect_columns(["id", "category"])


# --- labels ---------------------------------------------------------------------------------------
def test_labels_from_csv_and_fallback():
    assert labels.category_label("DemarchageAbusif") == "Phone or door-to-door solicitation"
    assert labels.category_label("TelephonieFaiMedias") == "Phone, internet provider & media"
    assert labels.status_label("ConsulteIgnore") == "Opened, ignored"
    assert labels.lookup("category", "ProduitsObjets") == ("Products items", False)
    assert labels.category_label(None) == labels.UNSPECIFIED


def test_issue_text_uses_deepest_level():
    raw = "Un_influenceur,Linfluenceur_nindique_pas_le_caractere_commercial"
    assert labels.issue_text(raw) == "Linfluenceur nindique pas le caractere commercial"
    assert labels.issue_text("") is None and labels.issue_text(None) is None


# --- geography ------------------------------------------------------------------------------------
def test_normalize_department_code():
    assert geo.normalize_code("75") == "75" and geo.normalize_code("2a") == "2A"
    assert geo.normalize_code("2") == "02" and geo.normalize_code("75.0") == "75"
    assert geo.normalize_code("974") == "974"
    assert geo.normalize_code("988") is None and geo.normalize_code("abc") is None
    assert geo.normalize_code(None) is None
    assert geo.code_from_name("Val-d'Oise") == "95"


def test_reference_table_is_complete():
    table = geo.departments()
    assert len(table) == 101 and table["code"].is_unique
    assert (table["population_k"] > 0).all()
    assert set(geo.OVERSEAS_CODES) <= set(table["code"])


# --- pipeline -------------------------------------------------------------------------------------
def test_map_unique_handles_missing():
    out = map_unique(pd.Series(["a", None, "b", "a"]), str.upper)
    assert out.tolist() == ["A", None, "B", "A"]


def test_read_header(tmp_path):
    path = make_csv(tmp_path / "x.csv", n=500)
    separator, header = read_header(path)
    assert separator == ";" and header == HEADER


def test_cleaning_counts(datasets):
    r = datasets.report
    assert r["rows_raw"] == N_VALID_ROWS + 25
    assert r["bad_dates"] == 40 and r["future_dates"] == 10 and r["before_launch"] == 10
    assert r["duplicates"] == 25
    assert r["missing_category"] >= 40
    assert r["rows_kept"] == r["rows_raw"] - r["rows_removed"] == int(datasets.cube["n"].sum())
    assert r["rows_removed"] >= 85


def test_cube_structure(datasets):
    cube = datasets.cube
    assert not cube.duplicated(["ym", "category", "dept"]).any()
    assert (cube["ym"].dt.day == 1).all()
    assert (cube["forwarded"] <= cube["n"]).all()
    assert (cube["read"] <= cube["forwarded"]).all() and (cube["answered"] <= cube["read"]).all()
    assert set(cube["dept"].astype(str)) >= {"75", "2A", "974", geo.UNLOCATED}   # 988 is not in the table
    assert "Unlocated" in set(cube["region"].astype(str))


def test_report_flags_and_labels(datasets):
    r = datasets.report
    assert r["has_geo"] and r["has_funnel"] and r["has_status"] and r["has_issues"]
    assert r["unmapped_categories"] == ["ProduitsObjets"]
    assert r["last_complete_month"] == "2026-09-01"
    assert "Online purchase" in set(datasets.cube["category"].astype(str))
    assert set(datasets.statuses["status"]) >= {"Unfounded", "Wrongly assigned"}
    assert datasets.issues["issue"].str.contains("_").sum() == 0


def test_new_sectors_start_in_2023(datasets):
    span = {row["category"]: row for row in datasets.report["taxonomy"]}
    assert span["Internet & social media"]["first_month"] >= "2023-01-01"
    assert span["Online purchase"]["last_month"] >= "2025-01-01"
