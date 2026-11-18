
"""Deterministic financial calculations. No LLM arithmetic."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(value: Any) -> Decimal:
    """Convert a value into a finite, safely rounded monetary Decimal."""

    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid monetary amounts.")

    try:
        amount = Decimal(str(value if value is not None else 0))

        if not amount.is_finite():
            raise ValueError("Monetary amounts must be finite numbers.")

        return amount.quantize(CENT, rounding=ROUND_HALF_UP)

    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid monetary amount: {value!r}"
        ) from exc


def _nonnegative_money(value: Any, field_name: str) -> Decimal:
    """Convert an amount and reject negative financial input."""

    amount = money(value)

    if amount < ZERO:
        raise ValueError(f"{field_name} cannot be negative.")

    return amount


def _to_date(value: Any, field_name: str) -> date | None:
    """Accept a date or ISO YYYY-MM-DD string."""

    if value is None:
        return None

    # datetime is a subclass of date, but mixing the two causes
    # comparison errors. Require a calendar date instead.
    if isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a date, not a datetime.")

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must use YYYY-MM-DD format."
            ) from exc

    raise TypeError(
        f"{field_name} must be a date, an ISO date string, or None."
    )


def outstanding(total: float, payments: list[float]) -> float:
    """Calculate the unpaid balance without allowing negative payments."""

    total_amount = _nonnegative_money(total, "Invoice total")
    paid = sum(
        (_nonnegative_money(payment, "Payment amount") for payment in payments),
        ZERO,
    )

    return float(max(ZERO, total_amount - paid))


def invoice_status(total: float, payments: list[float]) -> str:
    """Return unpaid, partially_paid, or paid."""

    total_amount = _nonnegative_money(total, "Invoice total")
    paid = sum(
        (_nonnegative_money(payment, "Payment amount") for payment in payments),
        ZERO,
    )

    if paid <= ZERO:
        return "unpaid"

    return "paid" if paid >= total_amount else "partially_paid"


def is_overdue(
    due_date: date | str | None,
    today: date,
    outstanding_amount: float,
) -> bool:
    """Return whether an invoice is past due and still has a balance."""

    normalized_due_date = _to_date(due_date, "Due date")
    normalized_today = _to_date(today, "Today's date")
    balance = _nonnegative_money(
        outstanding_amount,
        "Outstanding amount",
    )

    return (
        normalized_due_date is not None
        and normalized_today is not None
        and normalized_due_date < normalized_today
        and balance > ZERO
    )


def _required(record: dict, key: str, record_name: str) -> Any:
    """Read a required dictionary field with a clear error."""

    if key not in record or record[key] is None:
        raise ValueError(
            f"{record_name} is missing required field '{key}'."
        )

    return record[key]


def calculate_business_summary(
    invoices: list[dict],
    payments: list[dict],
    expenses: list[dict],
    business_id: str,
) -> dict:
    """
    Calculate financial summary for one business.

    Expected invoice fields:
        id, business_id, invoice_type, total_amount

    Expected payment fields:
        business_id, invoice_id, amount

    Expected expense fields:
        business_id, amount

    Payments are matched to invoices using invoice_id.
    All monetary arithmetic uses Decimal.
    """

    if business_id is None or not str(business_id).strip():
        raise ValueError("business_id must not be empty.")

    target_business_id = str(business_id)

    business_invoices = [
        invoice for invoice in invoices
        if str(invoice.get("business_id")) == target_business_id
    ]

    business_payments = [
        payment for payment in payments
        if str(payment.get("business_id")) == target_business_id
    ]

    business_expenses = [
        expense for expense in expenses
        if str(expense.get("business_id")) == target_business_id
    ]

    invoice_payments: dict[str, list[Decimal]] = {}

    for payment in business_payments:
        invoice_id = str(
            _required(payment, "invoice_id", "Payment")
        )
        amount = _nonnegative_money(
            _required(payment, "amount", "Payment"),
            "Payment amount",
        )

        invoice_payments.setdefault(invoice_id, []).append(amount)

    sales_total = ZERO
    expense_total = ZERO
    receivables = ZERO
    payables = ZERO

    for invoice in business_invoices:
        invoice_id = str(_required(invoice, "id", "Invoice"))
        total = _nonnegative_money(
            _required(invoice, "total_amount", "Invoice"),
            "Invoice total",
        )
        invoice_type = _required(
            invoice, "invoice_type", "Invoice"
        )

        if invoice_type not in {"sales", "purchase"}:
            raise ValueError(
                f"Unsupported invoice_type: {invoice_type!r}."
            )

        paid = sum(invoice_payments.get(invoice_id, []), ZERO)
        balance = max(ZERO, total - paid)

        if invoice_type == "sales":
            sales_total += total
            receivables += balance
        else:
            payables += balance

    for expense in business_expenses:
        expense_total += _nonnegative_money(
            _required(expense, "amount", "Expense"),
            "Expense amount",
        )

    return {
        "sales_total": float(sales_total),
        "expense_total": float(expense_total),
        "receivables": float(receivables),
        "payables": float(payables),
        "operating_surplus_estimate": float(
            sales_total - expense_total
        ),
    }


def get_overdue_invoices(
    invoices: list[dict],
    payments: list[dict],
    business_id: str,
    today: date,
) -> list[dict]:
    """Return overdue invoices for a specific business."""

    if business_id is None or not str(business_id).strip():
        raise ValueError("business_id must not be empty.")

    normalized_today = _to_date(today, "Today's date")
    if normalized_today is None:
        raise ValueError("Today's date is required.")

    target_business_id = str(business_id)
    payment_totals: dict[str, Decimal] = {}

    for payment in payments:
        if str(payment.get("business_id")) != target_business_id:
            continue

        invoice_id = str(
            _required(payment, "invoice_id", "Payment")
        )
        amount = _nonnegative_money(
            _required(payment, "amount", "Payment"),
            "Payment amount",
        )

        payment_totals[invoice_id] = (
            payment_totals.get(invoice_id, ZERO) + amount
        )

    overdue = []

    for invoice in invoices:
        if str(invoice.get("business_id")) != target_business_id:
            continue

        invoice_id = str(_required(invoice, "id", "Invoice"))
        total = _nonnegative_money(
            _required(invoice, "total_amount", "Invoice"),
            "Invoice total",
        )

        due_date = _to_date(
            invoice.get("due_date"),
            "Invoice due_date",
        )

        paid = payment_totals.get(invoice_id, ZERO)
        balance = max(ZERO, total - paid)

        if is_overdue(due_date, normalized_today, balance):
            overdue.append({
                "invoice_id": invoice_id,
                "invoice_number": invoice.get("invoice_number"),
                "party_name": invoice.get("party_name"),
                "outstanding": float(balance),
                "days_overdue": (
                    normalized_today - due_date
                ).days,
            })

    return overdue
