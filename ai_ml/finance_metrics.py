"""Deterministic money helpers (no LLM arithmetic)."""


def outstanding(total: float, payments: list[float]) -> float:
    return max(0.0, round(total - sum(payments), 2))


def invoice_status(total: float, payments: list[float]) -> str:
    paid = sum(payments)
    if paid <= 0:
        return "unpaid"
    return "paid" if paid >= total else "partially_paid"


def is_overdue(due_date, today, outstanding_amount: float) -> bool:
    return due_date is not None and due_date < today and outstanding_amount > 0
