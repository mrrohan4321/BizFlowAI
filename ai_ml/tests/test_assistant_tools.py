
from datetime import date

from ai_ml.assistant_tools import (
    get_receivables_summary,
    get_payables_summary,
    get_overdue_invoices_tool,
    get_monthly_performance,
    get_cash_forecast,
)


def sample_data():
    invoices = [
        {
            "id": "INV-102",
            "business_id": "BIZ-1",
            "invoice_type": "sales",
            "total_amount": 30000,
            "invoice_number": "INV-102",
            "party_name": "ABC Constructions",
            "due_date": date(2026, 11, 10),
        },
        {
            "id": "INV-103",
            "business_id": "BIZ-1",
            "invoice_type": "sales",
            "total_amount": 20000,
            "invoice_number": "INV-103",
            "party_name": "Raj Electricals",
            "due_date": date(2026, 11, 25),
        },
        {
            "id": "PUR-201",
            "business_id": "BIZ-1",
            "invoice_type": "purchase",
            "total_amount": 20000,
            "invoice_number": "PUR-201",
            "party_name": "XYZ Distributors",
            "due_date": date(2026, 11, 10),
        },
    ]

    payments = [
        {
            "business_id": "BIZ-1",
            "invoice_id": "INV-103",
            "amount": 5000,
        }
    ]

    return invoices, payments


def test_receivables_summary():
    invoices, payments = sample_data()

    result = get_receivables_summary(
        "BIZ-1", invoices, payments
    )

    assert result["receivables"] == 45000
    assert result["sales_total"] == 50000


def test_payables_summary():
    invoices, payments = sample_data()

    result = get_payables_summary(
        "BIZ-1", invoices, payments
    )

    assert result["payables"] == 20000


def test_overdue_invoices_tool():
    invoices, payments = sample_data()

    result = get_overdue_invoices_tool(
        "BIZ-1",
        invoices,
        payments,
        today=date(2026, 11, 18),
    )

    assert result["count"] == 2
    assert result["total_overdue"] == 50000


def test_monthly_performance():
    history = [
        {
            "month": "2026-08",
            "income": 30000,
            "outflows": 20000,
        },
        {
            "month": "2026-09",
            "income": 40000,
            "outflows": 25000,
        },
    ]

    result = get_monthly_performance("BIZ-1", history)

    assert result["total_income"] == 70000
    assert result["total_outflows"] == 45000
    assert result["net_cash_movement"] == 25000


def test_cash_forecast():
    history = [
        {"month": "2026-08", "income": 30000, "outflows": 20000},
        {"month": "2026-09", "income": 40000, "outflows": 25000},
        {"month": "2026-10", "income": 50000, "outflows": 30000},
    ]

    result = get_cash_forecast(
        "BIZ-1",
        history,
        opening_cash=100000,
        forecast_months=1,
    )

    assert result["business_id"] == "BIZ-1"
    assert result["closing_cash"] == 115000

import pytest


def test_monthly_performance_sorts_months_chronologically():
    history = [
        {"month": "2026-10", "income": 50, "outflows": 20},
        {"month": "2026-08", "income": 30, "outflows": 10},
        {"month": "2026-09", "income": 40, "outflows": 15},
    ]

    result = get_monthly_performance("BIZ-1", history)

    assert [
        item["month"] for item in result["monthly_data"]
    ] == ["2026-08", "2026-09", "2026-10"]


def test_monthly_performance_filters_other_businesses():
    history = [
        {
            "business_id": "BIZ-1",
            "month": "2026-08",
            "income": 100,
            "outflows": 40,
        },
        {
            "business_id": "BIZ-2",
            "month": "2026-08",
            "income": 900,
            "outflows": 300,
        },
    ]

    result = get_monthly_performance("BIZ-1", history)

    assert result["total_income"] == 100
    assert result["total_outflows"] == 40
    assert result["months_available"] == 1


def test_monthly_performance_uses_decimal_arithmetic():
    history = [
        {"month": "2026-08", "income": 0.1, "outflows": 0.1},
        {"month": "2026-09", "income": 0.2, "outflows": 0.2},
    ]

    result = get_monthly_performance("BIZ-1", history)

    assert result["total_income"] == 0.3
    assert result["total_outflows"] == 0.3
    assert result["net_cash_movement"] == 0.0


def test_monthly_performance_rejects_duplicate_months():
    history = [
        {"month": "2026-08", "income": 100, "outflows": 50},
        {"month": "2026-08-31", "income": 200, "outflows": 60},
    ]

    with pytest.raises(ValueError, match="Duplicate monthly history"):
        get_monthly_performance("BIZ-1", history)


@pytest.mark.parametrize(
    "invalid_amount",
    [-10, float("nan"), float("inf"), float("-inf"), True],
)
def test_monthly_performance_rejects_invalid_income(invalid_amount):
    history = [
        {
            "month": "2026-08",
            "income": invalid_amount,
            "outflows": 10,
        }
    ]

    with pytest.raises(ValueError):
        get_monthly_performance("BIZ-1", history)


def test_monthly_performance_rejects_negative_outflows():
    history = [
        {"month": "2026-08", "income": 100, "outflows": -10}
    ]

    with pytest.raises(ValueError, match="Monthly outflows cannot be negative"):
        get_monthly_performance("BIZ-1", history)


def test_monthly_performance_rejects_missing_month():
    history = [{"income": 100, "outflows": 50}]

    with pytest.raises(ValueError, match="missing 'month'"):
        get_monthly_performance("BIZ-1", history)


@pytest.mark.parametrize("invalid_business_id", ["", "   ", None])
def test_monthly_performance_rejects_invalid_business_id(
    invalid_business_id,
):
    with pytest.raises(ValueError, match="business_id"):
        get_monthly_performance(invalid_business_id, [])


def test_monthly_performance_rejects_non_list_history():
    with pytest.raises(TypeError, match="monthly_history must be a list"):
        get_monthly_performance("BIZ-1", None)

