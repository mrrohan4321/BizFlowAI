
"""Approved deterministic tools for the financial assistant."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .finance_metrics import (
    calculate_business_summary,
    get_overdue_invoices,
    money,
)
from .forecasting import get_forecast


ZERO = Decimal("0.00")


def _validate_business_id(business_id: str) -> None:
    """Ensure a valid business identifier was supplied."""
    if not isinstance(business_id, str) or not business_id.strip():
        raise ValueError("business_id must be a non-empty string.")


def _get_business_history(
    business_id: str,
    monthly_history: list[dict],
) -> list[dict]:
    """Filter monthly records for one business.

    Records without business_id are assumed to have already been
    scoped by the backend before reaching this module.
    """
    _validate_business_id(business_id)

    if not isinstance(monthly_history, list):
        raise TypeError("monthly_history must be a list.")

    return [
        item
        for item in monthly_history
        if isinstance(item, dict)
        and str(item.get("business_id", business_id)) == str(business_id)
    ]


def _month_sort_key(value: Any) -> date:
    """Convert a supported month value into a sortable date."""
    if isinstance(value, datetime):
        return value.date().replace(day=1)

    if isinstance(value, date):
        return value.replace(day=1)

    if isinstance(value, str):
        normalized = value.strip()

        if len(normalized) == 7:
            normalized += "-01"

        try:
            return date.fromisoformat(normalized).replace(day=1)
        except ValueError as exc:
            raise ValueError(
                "Each month must use YYYY-MM or YYYY-MM-DD format."
            ) from exc

    raise TypeError(
        "Each month must be a date, datetime, or ISO date string."
    )


def _nonnegative_amount(value: Any, field_name: str) -> Decimal:
    """Parse a finite, nonnegative monetary amount."""
    amount = money(value)

    if amount < ZERO:
        raise ValueError(f"{field_name} cannot be negative.")

    return amount


def get_receivables_summary(
    business_id: str,
    invoices: list[dict],
    payments: list[dict],
    expenses: list[dict] | None = None,
) -> dict:
    """Return sales and outstanding receivables for one business."""
    summary = calculate_business_summary(
        invoices=invoices,
        payments=payments,
        expenses=[] if expenses is None else expenses,
        business_id=business_id,
    )

    return {
        "business_id": business_id,
        "receivables": summary["receivables"],
        "sales_total": summary["sales_total"],
    }


def get_payables_summary(
    business_id: str,
    invoices: list[dict],
    payments: list[dict],
    expenses: list[dict] | None = None,
) -> dict:
    """Return outstanding purchase payables for one business."""
    summary = calculate_business_summary(
        invoices=invoices,
        payments=payments,
        expenses=[] if expenses is None else expenses,
        business_id=business_id,
    )

    return {
        "business_id": business_id,
        "payables": summary["payables"],
    }


def get_overdue_invoices_tool(
    business_id: str,
    invoices: list[dict],
    payments: list[dict],
    today: date | None = None,
) -> dict:
    """Return overdue invoices and their outstanding amounts."""
    _validate_business_id(business_id)

    overdue = get_overdue_invoices(
        invoices=invoices,
        payments=payments,
        business_id=business_id,
        today=today if today is not None else date.today(),
    )

    total_overdue = sum(
        (money(invoice["outstanding"]) for invoice in overdue),
        ZERO,
    )

    return {
        "business_id": business_id,
        "count": len(overdue),
        "total_overdue": float(total_overdue),
        "invoices": overdue,
    }


def get_monthly_performance(
    business_id: str,
    monthly_history: list[dict],
) -> dict:
    """Summarize monthly income and outflows for one business."""
    business_history = _get_business_history(
        business_id,
        monthly_history,
    )

    normalized_history = []
    seen_months = set()

    for item in business_history:
        if "month" not in item or item["month"] is None:
            raise ValueError("Monthly history record is missing 'month'.")

        month_key = _month_sort_key(item["month"])

        if month_key in seen_months:
            raise ValueError(
                f"Duplicate monthly history record: {month_key:%Y-%m}."
            )

        seen_months.add(month_key)

        income = _nonnegative_amount(
            item.get("income", 0),
            "Monthly income",
        )
        outflows = _nonnegative_amount(
            item.get("outflows", 0),
            "Monthly outflows",
        )

        normalized_history.append(
            {
                "sort_key": month_key,
                "month": item["month"],
                "income": income,
                "outflows": outflows,
            }
        )

    normalized_history.sort(key=lambda item: item["sort_key"])

    total_income = sum(
        (item["income"] for item in normalized_history),
        ZERO,
    )
    total_outflows = sum(
        (item["outflows"] for item in normalized_history),
        ZERO,
    )

    monthly_data = []

    for item in normalized_history:
        net_movement = item["income"] - item["outflows"]

        monthly_data.append(
            {
                "month": item["month"],
                "income": float(item["income"]),
                "outflows": float(item["outflows"]),
                "net_cash_movement": float(net_movement),
            }
        )

    return {
        "business_id": business_id,
        "months_available": len(normalized_history),
        "total_income": float(total_income),
        "total_outflows": float(total_outflows),
        "net_cash_movement": float(total_income - total_outflows),
        "monthly_data": monthly_data,
    }


def get_cash_forecast(
    business_id: str,
    monthly_history: list[dict],
    opening_cash: float,
    forecast_months: int = 3,
    window: int = 3,
) -> dict:
    """Generate a cash-flow forecast for one business."""
    business_history = _get_business_history(
        business_id,
        monthly_history,
    )

    result = get_forecast(
        monthly_history=business_history,
        opening_cash=opening_cash,
        forecast_months=forecast_months,
        window=window,
    )

    result["business_id"] = business_id

    return result


# Only these approved Python functions can be selected
# and executed by the AI assistant.
TOOLS: dict[str, Any] = {
    "get_receivables_summary": get_receivables_summary,
    "get_payables_summary": get_payables_summary,
    "get_overdue_invoices": get_overdue_invoices_tool,
    "get_monthly_performance": get_monthly_performance,
    "get_cash_forecast": get_cash_forecast,
}
