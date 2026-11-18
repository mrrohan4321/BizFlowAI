from app.db.database import get_cursor
from app.utils import serialize


def set_opening_cash(business_id: str, d) -> dict:
    with get_cursor() as cur:
        cur.execute("INSERT INTO opening_cash_balances (business_id, amount, as_of_date, note) VALUES (%s,%s,%s,%s) "
                    "ON CONFLICT (business_id, as_of_date) DO UPDATE SET amount = EXCLUDED.amount, note = EXCLUDED.note "
                    "RETURNING *", (business_id, d.amount, d.as_of_date, d.note))
        return serialize(cur.fetchone())


def list_opening_cash(business_id: str) -> list[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM opening_cash_balances WHERE business_id = %s ORDER BY as_of_date DESC", (business_id,))
        return [serialize(r) for r in cur.fetchall()]
