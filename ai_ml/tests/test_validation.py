
from decimal import Decimal

import pytest

from ai_ml import config
from ai_ml.schemas import InvoiceFields, Severity
from ai_ml.validation import validate_invoice


def make_valid_invoice(**overrides):
    data = {
        "invoice_number": "INV-001",
        "invoice_type": "sales",
        "party_name": "ABC Traders",
        "invoice_date": "2026-11-15",
        "due_date": "2026-11-30",
        "subtotal": "6000",
        "tax_amount": "1080",
        "cgst": "540",
        "sgst": "540",
        "total_amount": "7080",
        "gstin": "19ABCDE1234F1Z5",
    }
    data.update(overrides)
    return InvoiceFields(**data)


def test_valid_invoice_has_no_issues():
    assert validate_invoice(make_valid_invoice()) == []


def test_missing_invoice_number_generates_warning():
    issues = validate_invoice(
        make_valid_invoice(invoice_number=None)
    )

    assert any(
        issue.field == "invoice_number"
        and issue.severity == Severity.WARNING
        for issue in issues
    )


def test_total_amount_mismatch_generates_warning():
    issues = validate_invoice(
        make_valid_invoice(total_amount="8000")
    )

    assert any(
        issue.field == "total_amount"
        and issue.severity == Severity.WARNING
        for issue in issues
    )


def test_negative_amount_generates_error():
    issues = validate_invoice(
        make_valid_invoice(subtotal="-6000")
    )

    assert any(
        issue.field == "subtotal"
        and issue.severity == Severity.ERROR
        for issue in issues
    )


def test_due_date_before_invoice_date_generates_warning():
    issues = validate_invoice(
        make_valid_invoice(due_date="2026-11-10")
    )

    assert any(
        issue.field == "due_date"
        and issue.severity == Severity.WARNING
        for issue in issues
    )


def test_invalid_gstin_generates_warning():
    issues = validate_invoice(
        make_valid_invoice(gstin="INVALID-GSTIN")
    )

    assert any(
        issue.field == "gstin"
        and issue.severity == Severity.WARNING
        for issue in issues
    )


def test_cgst_and_sgst_mismatch_generates_warning():
    issues = validate_invoice(
        make_valid_invoice(cgst="300", sgst="300")
    )

    assert any(
        issue.field == "tax_amount"
        and issue.severity == Severity.WARNING
        for issue in issues
    )


def test_valid_igst_invoice_has_no_tax_mismatch():
    invoice = make_valid_invoice(
        igst="1080",
        cgst=None,
        sgst=None,
    )

    assert validate_invoice(invoice) == []


def test_igst_mismatch_generates_warning():
    invoice = make_valid_invoice(
        igst="900",
        cgst=None,
        sgst=None,
    )

    issues = validate_invoice(invoice)

    assert any(
        issue.field == "tax_amount"
        and issue.severity == Severity.WARNING
        for issue in issues
    )


def test_igst_and_cgst_together_generate_warning():
    invoice = make_valid_invoice(igst="1080")

    issues = validate_invoice(invoice)

    assert any(
        issue.field == "igst"
        and issue.severity == Severity.WARNING
        for issue in issues
    )


def test_missing_tax_components_do_not_generate_false_warning():
    invoice = make_valid_invoice(
        tax_amount="1080",
        cgst=None,
        sgst=None,
        igst=None,
    )

    assert validate_invoice(invoice) == []


def test_amount_difference_within_tolerance_is_accepted():
    invoice = make_valid_invoice(total_amount="7080.50")

    assert validate_invoice(invoice) == []


def test_amount_difference_above_tolerance_generates_warning():
    invoice = make_valid_invoice(total_amount="7081.01")

    issues = validate_invoice(invoice)

    assert any(
        issue.field == "total_amount"
        and issue.severity == Severity.WARNING
        for issue in issues
    )


def test_lowercase_gstin_is_accepted():
    invoice = make_valid_invoice(gstin="19abcde1234f1z5")

    assert validate_invoice(invoice) == []


def test_missing_invoice_type_generates_warning():
    issues = validate_invoice(
        make_valid_invoice(invoice_type=None)
    )

    assert any(
        issue.field == "invoice_type"
        and issue.severity == Severity.WARNING
        for issue in issues
    )


def test_negative_amount_does_not_trigger_arithmetic_warning():
    invoice = make_valid_invoice(
        subtotal="-6000",
        total_amount="7080",
    )

    issues = validate_invoice(invoice)

    assert any(
        issue.field == "subtotal"
        and issue.severity == Severity.ERROR
        for issue in issues
    )

    assert not any(
        issue.field == "total_amount"
        and issue.severity == Severity.WARNING
        for issue in issues
    )


def test_invalid_input_type_raises_error():
    with pytest.raises(TypeError):
        validate_invoice({"total_amount": 100})
