
"""Simple, explainable cash-flow forecasting.

Uses a recent-month moving average as the baseline.
No LLM arithmetic is involved.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(value: Any) -> Decimal:
    """Convert a value into a finite monetary Decimal."""

    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid monetary amounts.")

    try:
        amount = Decimal(str(value if value is not None else 0))

        if not amount.is_finite():
            raise ValueError("Monetary amounts must be finite.")

        return amount.quantize(CENT, rounding=ROUND_HALF_UP)

    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid monetary amount: {value!r}"
        ) from exc


def _nonnegative_money(value: Any, field_name: str) -> Decimal:
    """Convert an amount and reject negative historical income/outflows."""

    amount = money(value)

    if amount < ZERO:
        raise ValueError(f"{field_name} cannot be negative.")

    return amount


def _validate_positive_integer(value: Any, field_name: str) -> None:
    """Require a positive integer, excluding booleans."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer.")


def _normalize_month(value: Any) -> date:
    """Convert a supported month representation into its first day."""

    if isinstance(value, datetime):
        return date(value.year, value.month, 1)

    if isinstance(value, date):
        return date(value.year, value.month, 1)

    if isinstance(value, str):
        try:
            if len(value) == 7:
                parsed = date.fromisoformat(value + "-01")
            else:
                parsed = date.fromisoformat(value)

            return date(parsed.year, parsed.month, 1)

        except ValueError as exc:
            raise ValueError(
                "Month must use YYYY-MM or YYYY-MM-DD format."
            ) from exc

    raise TypeError(
        "Month must be a date, datetime, or ISO date string."
    )


def baseline_forecast(
    monthly_values: list[float],
    window: int = 12,
) -> float:
    """Predict the next month using the recent-month average."""

    _validate_positive_integer(window, "window")

    if not isinstance(monthly_values, (list, tuple)):
        raise TypeError("monthly_values must be a list or tuple.")

    recent = monthly_values[-window:]

    if not recent:
        return 0.0

    validated_values = [
        _nonnegative_money(value, "Historical value")
        for value in recent
    ]

    average = (
        sum(validated_values, ZERO) / Decimal(len(validated_values))
    )

    return float(average)


def get_forecast(
    monthly_history: list[dict],
    opening_cash: float = 0,
    forecast_months: int = 3,
    window: int = 12,
) -> dict:
    """
    Generate an explainable cash-flow forecast.

    Each monthly_history item must contain:
        month: date, YYYY-MM, or YYYY-MM-DD
        income: actual income received
        outflows: actual cash outflows

    opening_cash is the cash balance at the end of the last
    historical month. It may be negative, for example, an overdraft.

    Uses up to 12 recent historical months by default.
    If fewer than 12 months are available, all available months are used.

    Duplicate historical months are rejected to prevent distorted averages.
    """

    _validate_positive_integer(forecast_months, "forecast_months")
    _validate_positive_integer(window, "window")

    if not isinstance(monthly_history, (list, tuple)):
        raise TypeError("monthly_history must be a list or tuple.")

    opening_balance = money(opening_cash)

    # Empty history cannot support a meaningful forecast.
    if not monthly_history:
        return {
            "periods": [],
            "values": [],
            "method": "insufficient_data",
            "months_of_history_used": 0,
            "assumptions": [
                "No historical monthly data was provided.",
                "A reliable cash-flow forecast cannot be generated.",
            ],
            "opening_cash": float(opening_balance),
            "closing_cash": float(opening_balance),
        }

    # Validate and normalize historical records.
    history = []

    for index, item in enumerate(monthly_history):
        if not isinstance(item, dict):
            raise TypeError(
                f"History item {index} must be a dictionary."
            )

        for required_field in ("month", "income", "outflows"):
            if required_field not in item or item[required_field] is None:
                raise ValueError(
                    f"History item {index} is missing "
                    f"required field '{required_field}'."
                )

        normalized_month = _normalize_month(item["month"])

        income = _nonnegative_money(
            item["income"],
            "Historical income",
        )

        outflows = _nonnegative_money(
            item["outflows"],
            "Historical outflows",
        )

        history.append({
            "month": normalized_month,
            "income": income,
            "outflows": outflows,
        })

    # Sort records chronologically.
    history.sort(key=lambda item: item["month"])

    # Duplicate months could otherwise receive extra weight.
    months = [item["month"] for item in history]

    if len(months) != len(set(months)):
        raise ValueError(
            "Duplicate historical months are not allowed."
        )

    # Use only the requested number of recent months.
    recent_history = history[-window:]
    months_used = len(recent_history)

    income_history = [
        item["income"] for item in recent_history
    ]

    outflow_history = [
        item["outflows"] for item in recent_history
    ]

    predicted_income = money(
        baseline_forecast(income_history, window)
    )

    predicted_outflows = money(
        baseline_forecast(outflow_history, window)
    )

    # Forecast begins in the month after the last historical record.
    last_month = history[-1]["month"]
    current_month = last_month

    cash_balance = opening_balance

    periods = []
    values = []

    for _ in range(forecast_months):
        if current_month.month == 12:
            current_month = date(current_month.year + 1, 1, 1)
        else:
            current_month = date(
                current_month.year,
                current_month.month + 1,
                1,
            )

        cash_balance = money(
            cash_balance + predicted_income - predicted_outflows
        )

        periods.append(current_month.strftime("%Y-%m"))

        values.append({
            "predicted_income": float(predicted_income),
            "predicted_outflows": float(predicted_outflows),
            "predicted_closing_cash": float(cash_balance),
        })

    return {
        "periods": periods,
        "values": values,
        "method": f"{months_used}-month moving average",
        "months_of_history_used": months_used,
        "assumptions": [
            "Predictions use the average of the most recent historical months.",
            "Future income and outflows are assumed to remain at their predicted averages.",
            "Historical outflows represent cash leaving the business.",
            "Unpaid invoices are not counted as received income.",
            "Opening cash is the balance at the end of the last historical month.",
            "Negative opening cash is permitted, for example, an overdraft.",
            "This is an estimate, not a guarantee of future cash flow.",
        ],
        "opening_cash": float(opening_balance),
        "closing_cash": float(cash_balance),
    }
