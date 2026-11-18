import os
import re
import secrets
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import psycopg2
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-test-secret-test-secret-123456"
from app import config  # noqa: E402  (loads .env first)

config.SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]
TEST_DB = os.getenv("TEST_DATABASE_URL") or config.DATABASE_URL
TABLES = ("invoice_extractions, opening_cash_balances, business_members, forecasts, payments, expenses, "
          "invoices, customers, suppliers, businesses")


@pytest.fixture(scope="session", autouse=True)
def _isolated_schema():
    """All backend tests run in a throwaway schema, so a real database is never touched."""
    if not TEST_DB:
        pytest.skip("Set TEST_DATABASE_URL (or DATABASE_URL) to run backend tests")
    schema = "bf_test_" + secrets.token_hex(4)
    assert re.fullmatch(r"[a-z0-9_]+", schema)
    config.DATABASE_URL, config.DB_SCHEMA = TEST_DB, ""
    conn = psycopg2.connect(TEST_DB)
    conn.autocommit = True
    conn.cursor().execute(f"CREATE SCHEMA {schema}")
    config.DB_SCHEMA = schema
    from app.db import migrate
    migrate.run()
    yield schema
    config.DB_SCHEMA = ""
    conn.cursor().execute(f"DROP SCHEMA {schema} CASCADE")
    conn.close()


@pytest.fixture(autouse=True)
def _clean(_isolated_schema):
    from app.db.database import get_cursor
    with get_cursor() as cur:
        cur.execute(f"TRUNCATE {TABLES} CASCADE")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def make_token(user_id, expired=False, secret=None, aud="authenticated"):
    exp = datetime.now(timezone.utc) + timedelta(hours=-1 if expired else 1)
    return jwt.encode({"sub": str(user_id), "aud": aud, "exp": exp}, secret or config.SUPABASE_JWT_SECRET, "HS256")


class World:
    """Two businesses (A, B), each with one member, plus helpers."""

    def __init__(self):
        from app.db.database import get_cursor
        self.get_cursor = get_cursor
        self.user_a, self.user_b = uuid.uuid4(), uuid.uuid4()
        self.biz_a, self.biz_b = self._business("Biz A", self.user_a), self._business("Biz B", self.user_b)
        self.h_a = {"Authorization": f"Bearer {make_token(self.user_a)}"}
        self.h_b = {"Authorization": f"Bearer {make_token(self.user_b)}"}

    def _business(self, name, owner):
        with self.get_cursor() as cur:
            cur.execute("INSERT INTO businesses (name, owner_user_id) VALUES (%s,%s) RETURNING id", (name, owner))
            bid = cur.fetchone()["id"]
            cur.execute("INSERT INTO business_members (business_id, user_id, role) VALUES (%s,%s,'owner')", (bid, owner))
        return str(bid)

    def invoice(self, business_id, number="INV-1", kind="sales", total="1000.00", due="2026-11-01"):
        with self.get_cursor() as cur:
            cur.execute("INSERT INTO invoices (business_id, invoice_number, invoice_type, party_name, invoice_date, "
                        "due_date, total_amount) VALUES (%s,%s,%s,'Party','2026-10-01',%s,%s) RETURNING id",
                        (business_id, number, kind, due, total))
            return str(cur.fetchone()["id"])


@pytest.fixture
def world():
    return World()


# ---------- helpers for analytics / forecast / assistant tests ----------
def add_payment(world, business_id, invoice_id, amount, on):
    with world.get_cursor() as cur:
        cur.execute("INSERT INTO payments (business_id, invoice_id, amount, payment_date) VALUES (%s,%s,%s,%s)",
                    (business_id, invoice_id, amount, on))


def add_expense(world, business_id, amount, on, paid_on=None, category="rent"):
    with world.get_cursor() as cur:
        cur.execute("INSERT INTO expenses (business_id, category, amount, expense_date, payment_status, paid_date) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (business_id, category, amount, on, "paid" if paid_on else "unpaid", paid_on))


def set_opening(world, business_id, amount="100000.00", as_of="2026-10-31"):
    with world.get_cursor() as cur:
        cur.execute("INSERT INTO opening_cash_balances (business_id, amount, as_of_date) VALUES (%s,%s,%s)",
                    (business_id, amount, as_of))


def known_answer(world, business_id):
    """INV-102 30k unpaid | INV-103 20k with 5k paid | PUR-201 20k unpaid => receivables 45k, payables 20k."""
    i102 = world.invoice(business_id, "INV-102", "sales", "30000.00", due="2026-11-10")
    i103 = world.invoice(business_id, "INV-103", "sales", "20000.00", due="2026-11-25")
    p201 = world.invoice(business_id, "PUR-201", "purchase", "20000.00", due="2026-12-01")
    add_payment(world, business_id, i103, "5000.00", "2026-11-05")
    return i102, i103, p201
