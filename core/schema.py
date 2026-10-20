"""Column detection for the SignalConso CSV.

Headers are compared after normalisation (no accents, case or punctuation), so small changes
in the export ("Date" / "date", "Nom Officiel Région" / "nom_officiel_region") do not break the app.
Two fields are required; everything else is optional and the matching feature is switched off
when the column is missing.
"""
from __future__ import annotations

from .text import ascii_key

# canonical name -> accepted normalised headers
ACCEPTED_HEADERS: dict[str, tuple[str, ...]] = {
    "id": ("id",),
    "date": ("date", "creationdate"),
    "category": ("category",),
    "subcategories": ("subcategories",),
    "status": ("status",),
    "forwarded": ("signalementtransmis",),
    "read": ("signalementluparlentreprise",),
    "answered": ("signalementayantrecuunereponse",),
    "dep_code": ("depcode",),
    "dep_name": ("depname",),
}
REQUIRED = ("date", "category")


class SchemaError(ValueError):
    """Raised when a required column cannot be found."""


def detect_columns(header: list[str]) -> dict[str, str]:
    """Map canonical field names to the real column names of the file."""
    by_key: dict[str, str] = {}
    for column in header:
        by_key.setdefault(ascii_key(column), column)

    found: dict[str, str] = {}
    for field, keys in ACCEPTED_HEADERS.items():
        for key in keys:
            if key in by_key:
                found[field] = by_key[key]
                break

    missing = [field for field in REQUIRED if field not in found]
    if missing:
        raise SchemaError(
            f"Required column(s) not found: {missing}. Columns in the file: {header}. "
            "Add the new header name to ACCEPTED_HEADERS in core/schema.py."
        )
    return found
