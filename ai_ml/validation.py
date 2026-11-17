"""Deterministic invoice checks."""
from .invoice_extraction import ExtractedInvoice

TOLERANCE = 1.0  # rupees


def validate_invoice(fields: ExtractedInvoice) -> list[str]:
    """Return warnings: subtotal + tax vs total, missing required fields."""
    warnings: list[str] = []
    if fields.total_amount is None:
        warnings.append("total_amount missing")
    if fields.subtotal is not None and fields.tax_amount is not None and fields.total_amount is not None:
        if abs(fields.subtotal + fields.tax_amount - fields.total_amount) > TOLERANCE:
            warnings.append("subtotal + tax does not match total")
    return warnings
