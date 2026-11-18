from decimal import Decimal

from ai_ml.finance_metrics import invoice_status, money, outstanding  # source of truth for balances
from app.db.database import get_connection, get_cursor
from app.errors import AppError
from app.utils import serialize


def invoice_balance(total, payment_amounts) -> dict:
    amounts = [money(a) for a in payment_amounts]
    return {
        "amount_paid": float(sum(amounts, Decimal("0.00"))),  # plain aggregation of recorded payments
        "outstanding_amount": outstanding(total, amounts),
        "status": invoice_status(total, amounts),
    }


def record_payment(business_id: str, data) -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        # Row lock serialises concurrent payments on the same invoice (no overpayment race).
        cur.execute("SELECT id, invoice_number, invoice_type, total_amount FROM invoices "
                    "WHERE id = %s AND business_id = %s FOR UPDATE", (str(data.invoice_id), business_id))
        inv = cur.fetchone()
        if inv is None:
            raise AppError(404, "invoice_not_found", "Invoice not found.")
        cur.execute("SELECT amount FROM payments WHERE invoice_id = %s AND business_id = %s",
                    (inv["id"], business_id))
        before = [r["amount"] for r in cur.fetchall()]
        remaining = Decimal(str(outstanding(inv["total_amount"], before)))
        if money(data.amount) > remaining:
            raise AppError(422, "overpayment", "Payment exceeds the outstanding balance.",
                           {"outstanding_amount": float(remaining)})
        cur.execute("INSERT INTO payments (business_id, invoice_id, amount, payment_date, method, reference, note) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *",
                    (business_id, inv["id"], data.amount, data.payment_date, data.method, data.reference, data.note))
        pay = cur.fetchone()
        bal = invoice_balance(inv["total_amount"], before + [pay["amount"]])
    return {"payment": serialize(pay),
            "invoice": {"id": str(inv["id"]), "invoice_number": inv["invoice_number"],
                        "invoice_type": inv["invoice_type"], "total_amount": float(inv["total_amount"]), **bal}}


def list_payments(business_id: str, invoice_id=None, date_from=None, date_to=None, limit=100, offset=0) -> list[dict]:
    sql, args = "SELECT * FROM payments WHERE business_id = %s", [business_id]
    for clause, val in (("invoice_id = %s", invoice_id and str(invoice_id)),
                        ("payment_date >= %s", date_from), ("payment_date <= %s", date_to)):
        if val:
            sql += f" AND {clause}"
            args.append(val)
    sql += " ORDER BY payment_date DESC, created_at DESC LIMIT %s OFFSET %s"
    with get_cursor() as cur:
        cur.execute(sql, args + [limit, offset])
        return [serialize(r) for r in cur.fetchall()]
