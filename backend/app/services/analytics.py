"""Analytics, overdue, monthly history and forecast.

All records are read with a business_id filter and handed to ai_ml, which is the single
source of truth for receivables / payables / overdue / forecast maths.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal

from ai_ml.assistant_tools import get_overdue_invoices_tool, get_monthly_performance
from ai_ml.finance_metrics import calculate_business_summary, money
from ai_ml.forecasting import get_forecast
from app.db.database import get_cursor
from app.errors import AppError

log = logging.getLogger("bizflow")
ZERO = Decimal("0.00")


# ---------- loading (always scoped to one business) ----------
def load_records(cur, business_id: str, date_from: date | None = None, date_to: date | None = None):
    inv_sql, inv_args = ("SELECT id, business_id, invoice_number, invoice_type, party_name, invoice_date, due_date, "
                         "total_amount FROM invoices WHERE business_id = %s"), [business_id]
    exp_sql, exp_args = ("SELECT id, business_id, category, amount, expense_date, payment_status, paid_date "
                         "FROM expenses WHERE business_id = %s"), [business_id]
    if date_from:
        inv_sql += " AND invoice_date >= %s"; inv_args.append(date_from)
        exp_sql += " AND expense_date >= %s"; exp_args.append(date_from)
    if date_to:
        inv_sql += " AND invoice_date <= %s"; inv_args.append(date_to)
        exp_sql += " AND expense_date <= %s"; exp_args.append(date_to)
    cur.execute(inv_sql, inv_args)
    invoices = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT business_id, invoice_id, amount, payment_date FROM payments WHERE business_id = %s", (business_id,))
    payments = [dict(r) for r in cur.fetchall()]
    cur.execute(exp_sql, exp_args)
    expenses = [dict(r) for r in cur.fetchall()]
    return invoices, payments, expenses


def latest_opening_cash(cur, business_id: str) -> dict | None:
    cur.execute("SELECT amount, as_of_date FROM opening_cash_balances WHERE business_id = %s "
                "ORDER BY as_of_date DESC LIMIT 1", (business_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def _months_between(first: str, last: str) -> list[str]:
    y, m = int(first[:4]), int(first[5:7])
    ly, lm = int(last[:4]), int(last[5:7])
    out = []
    while (y, m) <= (ly, lm):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def cash_history(cur, business_id: str, up_to: date | None = None) -> list[dict]:
    """Actual cash per month: income = payments on SALES invoices, outflows = payments on PURCHASE
    invoices + expenses marked paid (by paid_date). Unpaid invoices/expenses are never cash.
    Months without any recorded cash movement between the first month and `up_to` are zero rows."""
    cur.execute("SELECT to_char(p.payment_date, 'YYYY-MM') AS month, i.invoice_type, SUM(p.amount) AS total "
                "FROM payments p JOIN invoices i ON i.id = p.invoice_id AND i.business_id = p.business_id "
                "WHERE p.business_id = %s GROUP BY 1, 2", (business_id,))
    income: dict[str, Decimal] = {}
    outflows: dict[str, Decimal] = {}
    for r in cur.fetchall():
        bucket = income if r["invoice_type"] == "sales" else outflows
        bucket[r["month"]] = bucket.get(r["month"], ZERO) + r["total"]
    cur.execute("SELECT to_char(paid_date, 'YYYY-MM') AS month, SUM(amount) AS total FROM expenses "
                "WHERE business_id = %s AND payment_status = 'paid' AND paid_date IS NOT NULL GROUP BY 1",
                (business_id,))
    for r in cur.fetchall():
        outflows[r["month"]] = outflows.get(r["month"], ZERO) + r["total"]

    cutoff = up_to.strftime("%Y-%m") if up_to else None
    months = sorted(m for m in set(income) | set(outflows) if cutoff is None or m <= cutoff)
    if not months:
        return []
    last = cutoff or months[-1]
    return [{"month": m, "income": income.get(m, ZERO), "outflows": outflows.get(m, ZERO)}
            for m in _months_between(months[0], last)]


# ---------- summary ----------
def summary(business_id: str, date_from: date | None, date_to: date | None) -> dict:
    with get_cursor() as cur:
        invoices, payments, expenses = load_records(cur, business_id, date_from, date_to)
        cur.execute("SELECT currency FROM businesses WHERE id = %s", (business_id,))
        biz = cur.fetchone()
    result = calculate_business_summary(invoices, payments, expenses, business_id)
    return {**result, "currency": biz["currency"] if biz else None,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "notes": ["sales_total and expense_total are recorded amounts, not cash received/paid.",
                      "operating_surplus_estimate = recorded sales - recorded expenses; it is not a cash balance or profit."]}


# ---------- overdue ----------
def overdue(business_id: str, as_of: date | None) -> dict:
    today = as_of or date.today()
    with get_cursor() as cur:
        invoices, payments, _ = load_records(cur, business_id)
    res = get_overdue_invoices_tool(business_id=business_id, invoices=invoices, payments=payments, today=today)
    types = {str(i["id"]): i["invoice_type"] for i in invoices}
    items = []
    for inv in res["invoices"]:
        kind = types.get(inv["invoice_id"])
        items.append({**inv, "invoice_type": kind, "direction": "receivable" if kind == "sales" else "payable"})
    # Receivables and payables are never added together.
    recv = sum((money(i["outstanding"]) for i in items if i["direction"] == "receivable"), ZERO)
    pay = sum((money(i["outstanding"]) for i in items if i["direction"] == "payable"), ZERO)
    return {"as_of": today.isoformat(), "count": res["count"],
            "overdue_receivables_total": float(recv), "overdue_payables_total": float(pay), "invoices": items}


# ---------- monthly ----------
def monthly(business_id: str) -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT to_char(invoice_date, 'YYYY-MM') AS month, SUM(total_amount) AS total FROM invoices "
                    "WHERE business_id = %s AND invoice_type = 'sales' AND invoice_date IS NOT NULL GROUP BY 1",
                    (business_id,))
        sales = {r["month"]: r["total"] for r in cur.fetchall()}
        cur.execute("SELECT to_char(expense_date, 'YYYY-MM') AS month, SUM(amount) AS total FROM expenses "
                    "WHERE business_id = %s GROUP BY 1", (business_id,))
        expenses = {r["month"]: r["total"] for r in cur.fetchall()}
        history = cash_history(cur, business_id)
    cash_in = {h["month"]: h["income"] for h in history}
    cash_out = {h["month"]: h["outflows"] for h in history}
    labels = sorted(set(sales) | set(expenses) | set(cash_in) | set(cash_out))
    f = lambda d, m: float(d.get(m, ZERO))  # noqa: E731
    perf = get_monthly_performance(business_id=business_id, monthly_history=history)
    return {"labels": labels,
            "sales": [f(sales, m) for m in labels], "expenses": [f(expenses, m) for m in labels],
            "cash_income": [f(cash_in, m) for m in labels], "cash_outflows": [f(cash_out, m) for m in labels],
            "cash_summary": {k: perf[k] for k in ("months_available", "total_income", "total_outflows", "net_cash_movement")},
            "notes": ["sales/expenses are recorded by invoice/expense date; cash_* are actual money moved (payments and paid expenses)."]}


# ---------- forecast ----------
def _is_month_end(d: date) -> bool:
    return (d + timedelta(days=1)).day == 1


def forecast(business_id: str, months: int, window: int) -> dict:
    with get_cursor() as cur:
        opening = latest_opening_cash(cur, business_id)
        if opening is None:
            raise AppError(409, "opening_cash_required",
                           "Set the opening cash balance first (PUT /api/opening-cash) to get a cash-flow forecast.")
        if not _is_month_end(opening["as_of_date"]):
            raise AppError(422, "opening_cash_not_month_end",
                           "The latest opening cash balance must be dated on the last day of a month.")
        history = cash_history(cur, business_id, up_to=opening["as_of_date"])
    result = get_forecast(history, opening_cash=opening["amount"], forecast_months=months, window=window)
    insufficient = result["method"] == "insufficient_data"
    warnings = []
    if insufficient:
        warnings.append("No cash history is recorded up to the opening-cash date, so no forecast can be made.")
    elif result["months_of_history_used"] < window:
        warnings.append(f"Only {result['months_of_history_used']} month(s) of history are available "
                        f"(window is {window}); treat this estimate with extra caution.")
    result["assumptions"] = list(result["assumptions"]) + [
        "History = payments on sales invoices (income) and payments on purchase invoices plus expenses marked paid (outflows).",
        "Months without recorded cash movement count as zero.",
        "Record a cost as a purchase invoice OR an expense, not both, to avoid double counting."]
    return {**result, "insufficient_data": insufficient, "warnings": warnings, "is_estimate": True,
            "opening_cash_as_of": opening["as_of_date"].isoformat(),
            "disclaimer": "This is an estimate based on recorded history, not a guarantee."}
