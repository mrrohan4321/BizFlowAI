from tests.conftest import add_expense, add_payment, known_answer


def test_unauthenticated_analytics_rejected(client):
    for url in ("/api/analytics/summary", "/api/analytics/monthly", "/api/analytics/overdue",
                "/api/payments/overdue", "/api/forecast"):
        r = client.get(url)
        assert r.status_code == 401 and r.json()["error"]["code"] == "unauthenticated", url


def test_summary_known_answer_and_payment_updates_it(client, world):
    i102, _, _ = known_answer(world, world.biz_a)
    s = client.get("/api/analytics/summary", headers=world.h_a).json()
    assert s["receivables"] == 45000.0 and s["payables"] == 20000.0 and s["sales_total"] == 50000.0
    r = client.post("/api/payments", headers=world.h_a,
                    json={"invoice_id": i102, "amount": "10000.00", "payment_date": "2026-11-12"})
    assert r.status_code == 201
    s = client.get("/api/analytics/summary", headers=world.h_a).json()
    assert s["receivables"] == 35000.0 and s["payables"] == 20000.0


def test_purchase_invoices_never_count_as_receivables(client, world):
    world.invoice(world.biz_a, "PUR-1", "purchase", "999.00")
    s = client.get("/api/analytics/summary", headers=world.h_a).json()
    assert s["receivables"] == 0 and s["payables"] == 999.0 and s["sales_total"] == 0


def test_summary_expenses_and_surplus(client, world):
    known_answer(world, world.biz_a)
    add_expense(world, world.biz_a, "12000.00", "2026-10-05")
    s = client.get("/api/analytics/summary", headers=world.h_a).json()
    assert s["expense_total"] == 12000.0 and s["operating_surplus_estimate"] == 38000.0


def test_summary_is_isolated_between_businesses(client, world):
    known_answer(world, world.biz_a)
    world.invoice(world.biz_b, "B-1", "sales", "777.00")
    b = client.get("/api/analytics/summary", headers=world.h_b).json()
    assert b["receivables"] == 777.0 and b["payables"] == 0
    a = client.get("/api/analytics/summary", headers=world.h_a).json()
    assert a["receivables"] == 45000.0


def test_summary_date_range(client, world):
    world.invoice(world.biz_a, "OLD", "sales", "100.00")  # invoice_date 2026-10-01
    with world.get_cursor() as cur:
        cur.execute("UPDATE invoices SET invoice_date='2026-12-15' WHERE invoice_number='OLD'")
    world.invoice(world.biz_a, "NEW", "sales", "250.00")
    s = client.get("/api/analytics/summary?date_from=2026-10-01&date_to=2026-10-31", headers=world.h_a).json()
    assert s["sales_total"] == 250.0
    assert client.get("/api/analytics/summary?date_from=2026-12-01&date_to=2026-01-01",
                      headers=world.h_a).status_code == 422


def test_empty_business_returns_zeros(client, world):
    s = client.get("/api/analytics/summary", headers=world.h_a).json()
    assert (s["receivables"], s["payables"], s["sales_total"], s["expense_total"]) == (0, 0, 0, 0)


def test_overdue_uses_due_date_and_balance(client, world):
    i102, i103, p201 = known_answer(world, world.biz_a)
    o = client.get("/api/payments/overdue?as_of=2026-11-18", headers=world.h_a).json()
    assert o["count"] == 1
    inv = o["invoices"][0]
    assert (inv["invoice_number"], inv["days_overdue"], inv["outstanding"]) == ("INV-102", 8, 30000.0)
    assert inv["invoice_type"] == "sales" and inv["direction"] == "receivable"
    assert o["overdue_receivables_total"] == 30000.0 and o["overdue_payables_total"] == 0
    # fully paying it removes it from overdue
    add_payment(world, world.biz_a, i102, "30000.00", "2026-11-17")
    assert client.get("/api/analytics/overdue?as_of=2026-11-18", headers=world.h_a).json()["count"] == 0


def test_overdue_keeps_payables_separate_and_isolated(client, world):
    world.invoice(world.biz_a, "PUR-9", "purchase", "400.00", due="2026-11-01")
    world.invoice(world.biz_a, "INV-9", "sales", "100.00", due="2026-11-01")
    world.invoice(world.biz_b, "B-OVER", "sales", "5000.00", due="2026-11-01")
    o = client.get("/api/analytics/overdue?as_of=2026-11-18", headers=world.h_a).json()
    assert o["count"] == 2 and o["overdue_receivables_total"] == 100.0 and o["overdue_payables_total"] == 400.0
    assert all(i["invoice_number"] != "B-OVER" for i in o["invoices"])


def test_invoice_without_due_date_is_never_overdue(client, world):
    world.invoice(world.biz_a, "NODUE", "sales", "50.00", due=None)
    assert client.get("/api/analytics/overdue?as_of=2030-01-01", headers=world.h_a).json()["count"] == 0


def test_monthly_series(client, world):
    i102, i103, _ = known_answer(world, world.biz_a)
    add_expense(world, world.biz_a, "8000.00", "2026-10-04", paid_on="2026-10-05")
    add_expense(world, world.biz_a, "3000.00", "2026-11-02")  # unpaid: expense yes, cash no
    m = client.get("/api/analytics/monthly", headers=world.h_a).json()
    assert m["labels"] == ["2026-10", "2026-11"]
    assert m["sales"] == [50000.0, 0.0]               # both sales invoices dated 2026-10-01
    assert m["expenses"] == [8000.0, 3000.0]
    assert m["cash_income"] == [0.0, 5000.0]          # INV-103 part payment in Nov
    assert m["cash_outflows"] == [8000.0, 0.0]        # unpaid Nov expense is not an outflow
    assert m["cash_summary"]["months_available"] == 2


def test_monthly_empty_and_isolated(client, world):
    add_expense(world, world.biz_b, "1.00", "2026-10-01", paid_on="2026-10-01")
    m = client.get("/api/analytics/monthly", headers=world.h_a).json()
    assert m["labels"] == [] and m["sales"] == []
