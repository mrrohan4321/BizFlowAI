from app.db.database import get_cursor
from app.errors import AppError
from app.utils import serialize


def create_expense(business_id: str, d) -> dict:
    with get_cursor() as cur:
        cur.execute("INSERT INTO expenses (business_id, category, amount, expense_date, description, notes, "
                    "payment_status, paid_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
                    (business_id, d.category, d.amount, d.expense_date, d.description, d.notes,
                     d.payment_status, d.paid_date))
        return serialize(cur.fetchone())


def list_expenses(business_id: str, category=None, payment_status=None, date_from=None, date_to=None,
                  limit=100, offset=0) -> list[dict]:
    sql, args = "SELECT * FROM expenses WHERE business_id = %s", [business_id]
    for clause, val in (("category = %s", category), ("payment_status = %s", payment_status),
                        ("expense_date >= %s", date_from), ("expense_date <= %s", date_to)):
        if val:
            sql += f" AND {clause}"
            args.append(val)
    sql += " ORDER BY expense_date DESC, created_at DESC LIMIT %s OFFSET %s"
    with get_cursor() as cur:
        cur.execute(sql, args + [limit, offset])
        return [serialize(r) for r in cur.fetchall()]


def update_expense(business_id: str, expense_id: str, d) -> dict:
    changes = d.model_dump(exclude_unset=True)
    with get_cursor() as cur:
        cur.execute("SELECT * FROM expenses WHERE id = %s AND business_id = %s FOR UPDATE", (expense_id, business_id))
        row = cur.fetchone()
        if row is None:
            raise AppError(404, "expense_not_found", "Expense not found.")
        merged = {**row, **changes}
        if "payment_status" in changes and changes["payment_status"] == "unpaid" and "paid_date" not in changes:
            merged["paid_date"] = None
        if merged["payment_status"] == "paid" and merged["paid_date"] is None:
            raise AppError(422, "invalid_request", "paid_date is required when payment_status is 'paid'.")
        if merged["payment_status"] == "unpaid" and merged["paid_date"] is not None:
            raise AppError(422, "invalid_request", "paid_date must be empty when payment_status is 'unpaid'.")
        cur.execute("UPDATE expenses SET category=%s, description=%s, notes=%s, payment_status=%s, paid_date=%s "
                    "WHERE id=%s AND business_id=%s RETURNING *",
                    (merged["category"], merged["description"], merged["notes"], merged["payment_status"],
                     merged["paid_date"], expense_id, business_id))
        return serialize(cur.fetchone())
