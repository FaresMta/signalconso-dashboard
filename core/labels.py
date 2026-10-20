"""English labels for the coded values of the source file.

The source stores categories and statuses as CamelCase codes without accents
("TelephonieFaiMedias"). Labels come from data/reference/labels_en.csv; a code that is not in that
file gets a best-effort label built word by word from TOKENS, and is listed as "unmapped" in the
data-quality tab so it can be added to the CSV.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache

import pandas as pd

from . import config

UNSPECIFIED = "Unspecified"
UNKNOWN_STATUS = "Unknown"

# French word (lower case) -> English, used only when a code is missing from labels_en.csv
TOKENS = {
    "achat": "purchase", "magasin": "store", "internet": "internet", "demarchage": "solicitation",
    "abusif": "abusive", "travaux": "works", "renovation": "renovation", "renovations": "renovation",
    "voyage": "travel", "loisirs": "leisure", "telephonie": "phone", "fai": "ISP", "medias": "media",
    "banque": "bank", "assurance": "insurance", "mutuelle": "health plan", "voiture": "car",
    "vehicule": "vehicle", "velo": "bike", "cafe": "café", "restaurant": "restaurant", "sante": "health",
    "eau": "water", "gaz": "gas", "electricite": "electricity", "immobilier": "real estate",
    "animaux": "animals", "services": "services", "service": "service", "aux": "for",
    "particuliers": "individuals", "produits": "products", "objets": "items", "alimentation": "food",
    "transport": "transport", "transports": "transport", "aerien": "air", "education": "education",
    "sport": "sport", "influenceur": "influencer", "non": "not", "consulte": "read", "ignore": "ignored",
    "promesse": "promised", "action": "action", "infonde": "unfounded", "mal": "wrongly",
    "attribue": "assigned", "traitement": "processing", "en": "in", "cours": "progress", "et": "and",
}


@lru_cache(maxsize=1)
def _table() -> dict[tuple[str, str], str]:
    path = config.REFERENCE_DIR / "labels_en.csv"
    with open(path, encoding="utf-8", newline="") as handle:
        return {(row["field"], row["code"]): row["label"] for row in csv.DictReader(handle)}


def _fallback(code: str) -> str:
    """Split CamelCase / snake_case and translate known words: "BanqueAssurance" -> "Bank insurance"."""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", code.replace("_", " ")).split()
    text = " ".join(TOKENS.get(word.lower(), word.lower()) for word in words)
    return text[:1].upper() + text[1:]


def lookup(field: str, code: str) -> tuple[str, bool]:
    """Return (label, found_in_labels_csv)."""
    label = _table().get((field, code))
    return (label, True) if label else (_fallback(code), False)


def category_label(code: object) -> str:
    return UNSPECIFIED if _is_blank(code) else lookup("category", str(code).strip())[0]


def status_label(code: object) -> str:
    return UNKNOWN_STATUS if _is_blank(code) else lookup("status", str(code).strip())[0]


def issue_text(raw: object) -> str | None:
    """Most specific level of the `subcategories` path ("level1,level2" -> "level2").

    Texts stay in the original French (the source has no translation). Apostrophes and accents are
    absent in the source, and underscores replace spaces; only the underscores are restored here.
    """
    if _is_blank(raw):
        return None
    parts = [part.strip() for part in str(raw).split(",") if part.strip()]
    if not parts:
        return None
    text = parts[-1].replace("_", " ")
    return text[:1].upper() + text[1:]


def _is_blank(value: object) -> bool:
    return value is None or bool(pd.isna(value)) or not str(value).strip()
