"""Tiny text helpers shared by the schema, label and geography modules."""
from __future__ import annotations

import re
import unicodedata


def ascii_key(value: object) -> str:
    """Lower-case, accent-free, letters and digits only: "Département" -> "departement"."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text.lower())
