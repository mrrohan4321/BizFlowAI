from decimal import Decimal
from uuid import UUID


def serialize(row: dict | None) -> dict | None:
    """DB row -> JSON-friendly dict (Decimal -> number, UUID -> str), matching API-notes.md."""
    if row is None:
        return None
    out = {}
    for k, v in row.items():
        out[k] = float(v) if isinstance(v, Decimal) else str(v) if isinstance(v, UUID) else v
    return out
