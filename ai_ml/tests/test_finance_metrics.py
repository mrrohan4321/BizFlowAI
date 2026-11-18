
from datetime import date
import pytest

from ai_ml.finance_metrics import (
    money,
    outstanding,
    invoice_status,
    is_overdue,
    calculate_business_summary,
    get_overdue_invoices,
)

# --------------------------------------------------
# Basic financial helper tests
# --------------------------------------------------

def test_outstanding_balance():
    result = outstanding(30000, [5000, 10000])
    assert result == 15000


def test_fully_paid_invoice():
    result = invoice_status(20000, [10000, 10000])
    assert result == "paid"


def test_partially_paid_invoice():
    result = invoice_status(20000, [5000])
    assert result == "partially_paid"


def test_unpaid_invoice():
    result = invoice_status(20000, [])
    assert result == "unpaid"


def test_overdue_invoice():
    result = is_overdue(
        date(2026, 11, 10),
        date(2026, 11, 18),
        15000,
    )
    assert result is True


def test_not_overdue_invoice():
    result = is_overdue(
        date(2026, 11, 25),
        date(2026, 11, 18),
        15000,
    )
    assert result is False


def test_paid_invoice_is_not_overdue():
    result = is_overdue(
        date(2026, 11, 10),
        date(2026, 11, 18),
        0,
    )
    assert result is False


# --------------------------------------------------
# Business financial summary tests
# --------------------------------------------------

def test_business_financial_summary():
    invoices = [
        {
            "id": "INV-102",
            "business_id": "BIZ-1",
            "invoice_type": "sales",
            "total_amount": 30000,
        },
        {
            "id": "INV-103",
            "business_id": "BIZ-1",
            "invoice_type": "sales",
            "total_amount": 20000,
        },
        {
            "id": "PUR-201",
            "business_id": "BIZ-1",
            "invoice_type": "purchase",
            "total_amount": 20000,
        },
    ]

    payments = [
        {
            "business_id": "BIZ-1",
            "invoice_id": "INV-103",
            "amount": 5000,
        }
    ]

    expenses = [
        {"business_id": "BIZ-1", "amount": 10000}
    ]

    result = calculate_business_summary(
        invoices, payments, expenses, "BIZ-1"
    )

    assert result["sales_total"] == 50000
    assert result["expense_total"] == 10000
    assert result["receivables"] == 45000
    assert result["payables"] == 20000
    assert result["operating_surplus_estimate"] == 40000


def test_business_summary_excludes_other_business():
    invoices = [
        {
            "id": "INV-1",
            "business_id": "BIZ-1",
            "invoice_type": "sales",
            "total_amount": 10000,
        },
        {
            "id": "INV-2",
            "business_id": "BIZ-2",
            "invoice_type": "sales",
            "total_amount": 90000,
        },
    ]

    result = calculate_business_summary(
        invoices, [], [], "BIZ-1"
    )

    assert result["sales_total"] == 10000
    assert result["receivables"] == 10000


# --------------------------------------------------
# Overdue invoice tests
# --------------------------------------------------

def test_get_overdue_invoices():
    invoices = [
        {
            "id": "INV-1",
            "business_id": "BIZ-1",
            "invoice_number": "INV-102",
            "invoice_type": "sales",
            "party_name": "ABC Traders",
            "total_amount": 30000,
            "due_date": date(2026, 11, 10),
        }
    ]

    overdue = get_overdue_invoices(
        invoices,
        [],
        "BIZ-1",
        date(2026, 11, 18),
    )

    assert len(overdue) == 1
    assert overdue[0]["outstanding"] == 30000
    assert overdue[0]["days_overdue"] == 8


def test_fully_paid_invoice_not_in_overdue_list():
    invoices = [
        {
            "id": "INV-1",
            "business_id": "BIZ-1",
            "invoice_number": "INV-102",
            "total_amount": 30000,
            "due_date": date(2026, 11, 10),
        }
    ]

    payments = [
        {
            "business_id": "BIZ-1",
            "invoice_id": "INV-1",
            "amount": 30000,
        }
    ]

    overdue = get_overdue_invoices(
        invoices,
        payments,
        "BIZ-1",
        date(2026, 11, 18),
    )

    assert overdue == []

# --------------------------------------------------
# Financial input safety tests
# --------------------------------------------------

@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -float("inf")])
def test_money_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        money(value)


def test_money_rounds_to_two_decimal_places():
    assert money("123.456") == money("123.46")


def test_outstanding_rejects_negative_payment():
    with pytest.raises(ValueError, match="Payment amount cannot be negative"):
        outstanding(1000, [200, -50])


def test_invoice_status_rejects_negative_payment():
    with pytest.raises(ValueError, match="Payment amount cannot be negative"):
        invoice_status(1000, [-100])


def test_business_summary_rejects_negative_invoice_total():
    invoices = [{
        "id": "INV-1",
        "business_id": "BIZ-1",
        "invoice_type": "sales",
        "total_amount": -1000,
    }]

    with pytest.raises(ValueError, match="Invoice total cannot be negative"):
        calculate_business_summary(invoices, [], [], "BIZ-1")


def test_business_summary_rejects_negative_expense():
    expenses = [{
        "business_id": "BIZ-1",
        "amount": -500,
    }]

    with pytest.raises(ValueError, match="Expense amount cannot be negative"):
        calculate_business_summary([], [], expenses, "BIZ-1")


def test_overdue_invoice_accepts_iso_date_string():
    result = is_overdue(
        "2026-11-10",
        date(2026, 11, 18),
        500,
    )

    assert result is True


def test_overdue_invoice_rejects_invalid_date_string():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        is_overdue(
            "10-11-2026",
            date(2026, 11, 18),
            500,
        )


def test_get_overdue_invoices_accepts_iso_date_string():
    invoices = [{
        "id": "INV-1",
        "business_id": "BIZ-1",
        "invoice_number": "INV-101",
        "total_amount": 1000,
        "due_date": "2026-11-10",
    }]

    result = get_overdue_invoices(
        invoices,
        [],
        "BIZ-1",
        date(2026, 11, 18),
    )

    assert len(result) == 1
    assert result[0]["days_overdue"] == 8


def test_business_summary_rejects_missing_required_invoice_field():
    invoices = [{
        "business_id": "BIZ-1",
        "invoice_type": "sales",
        "total_amount": 1000,
    }]

    with pytest.raises(ValueError, match="id"):
        calculate_business_summary(invoices, [], [], "BIZ-1")


def test_payments_from_other_business_are_excluded():
    invoices = [{
        "id": "INV-1",
        "business_id": "BIZ-1",
        "invoice_type": "sales",
        "total_amount": 1000,
    }]

    payments = [
        {
            "business_id": "BIZ-2",
            "invoice_id": "INV-1",
            "amount": 1000,
        }
    ]

    result = calculate_business_summary(
        invoices, payments, [], "BIZ-1"
    )

    assert result["receivables"] == 1000

