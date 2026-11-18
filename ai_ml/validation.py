
"""Deterministic validation checks for extracted invoices."""

import re
from decimal import Decimal

from ai_ml import config
from ai_ml.schemas import InvoiceFields, Severity, ValidationIssue


GSTIN_PATTERN = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"
)


def validate_invoice(fields: InvoiceFields) -> list[ValidationIssue]:
    """Check invoice fields for missing or inconsistent information.

    These checks are deterministic. They do not verify GST registration
    against the government database or establish legal tax compliance.
    """

    if not isinstance(fields, InvoiceFields):
        raise TypeError("fields must be an InvoiceFields instance.")

    issues: list[ValidationIssue] = []
    tolerance = config.AMOUNT_TOLERANCE

    def add_issue(
        field: str,
        severity: Severity,
        message: str,
    ) -> None:
        issues.append(
            ValidationIssue(
                field=field,
                severity=severity,
                message=message,
            )
        )

    # 1. Check important fields.
    required_fields = {
        "invoice_number": fields.invoice_number,
        "party_name": fields.party_name,
        "invoice_date": fields.invoice_date,
        "total_amount": fields.total_amount,
        "invoice_type": fields.invoice_type,
    }

    for field_name, value in required_fields.items():
        if value is None:
            add_issue(
                field_name,
                Severity.WARNING,
                f"{field_name} is missing. Please review the invoice.",
            )

    # 2. Check negative monetary values.
    amount_fields = {
        "subtotal": fields.subtotal,
        "tax_amount": fields.tax_amount,
        "cgst": fields.cgst,
        "sgst": fields.sgst,
        "igst": fields.igst,
        "total_amount": fields.total_amount,
    }

    for field_name, value in amount_fields.items():
        if value is not None and value < 0:
            add_issue(
                field_name,
                Severity.ERROR,
                f"{field_name} cannot be negative.",
            )

    # Do not perform arithmetic consistency checks using negative amounts.
    has_negative_amount = any(
        value is not None and value < 0
        for value in amount_fields.values()
    )

    # 3. Check subtotal + tax = total.
    if (
        not has_negative_amount
        and fields.subtotal is not None
        and fields.tax_amount is not None
        and fields.total_amount is not None
    ):
        calculated_total = fields.subtotal + fields.tax_amount

        if abs(calculated_total - fields.total_amount) > tolerance:
            add_issue(
                "total_amount",
                Severity.WARNING,
                "Subtotal + tax does not match the invoice total.",
            )

    # 4. Check tax components against declared tax.
    # IGST and CGST/SGST represent alternative tax structures.
    has_igst = fields.igst is not None and fields.igst > 0
    has_cgst = fields.cgst is not None and fields.cgst > 0
    has_sgst = fields.sgst is not None and fields.sgst > 0

    if has_igst and (has_cgst or has_sgst):
        add_issue(
            "igst",
            Severity.WARNING,
            "IGST and CGST/SGST are both present. "
            "Please review the tax details.",
        )

    elif (
        not has_negative_amount
        and fields.tax_amount is not None
        and fields.igst is not None
        and fields.igst >= 0
        and fields.cgst is None
        and fields.sgst is None
        and abs(fields.igst - fields.tax_amount) > tolerance
    ):
        add_issue(
            "tax_amount",
            Severity.WARNING,
            "IGST does not match the declared tax amount.",
        )

    elif (
        not has_negative_amount
        and fields.tax_amount is not None
        and fields.cgst is not None
        and fields.sgst is not None
        and abs(
            fields.cgst + fields.sgst - fields.tax_amount
        ) > tolerance
    ):
        add_issue(
            "tax_amount",
            Severity.WARNING,
            "CGST + SGST does not match the declared tax amount.",
        )

    # 5. Check invoice dates.
    if (
        fields.invoice_date is not None
        and fields.due_date is not None
        and fields.due_date < fields.invoice_date
    ):
        add_issue(
            "due_date",
            Severity.WARNING,
            "Due date is earlier than invoice date.",
        )

    # 6. Check basic GSTIN format.
    # Uppercase normalization is performed for checking only.
    if fields.gstin is not None:
        gstin = fields.gstin.strip().upper()

        if not GSTIN_PATTERN.fullmatch(gstin):
            add_issue(
                "gstin",
                Severity.WARNING,
                "GSTIN format appears invalid. Please verify it.",
            )

    return issues
