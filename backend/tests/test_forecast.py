from tests.conftest import add_expense, add_payment, set_opening


def history(world, biz):
    """Aug/Sep/Oct 2026 actual cash: income 30k/60k/60k, outflows 10k/20k/30k (paid expenses)."""
    sale = world.invoice(biz, "S-1", "sales", "150000.00", due="2026-12-31")
    for amount, on in (("30000.00", "2026-08-10"), ("60000.00", "2026-09-10"), ("60000.00", "2026-10-10")):
        add_payment(world, biz, sale, amount, on)
    for amount, on in (("10000.00", "2026-08-20"), ("20000.00", "2026-09-20"), ("30000.00", "2026-10-20")):
        add_expense(world, biz, amount, on, paid_on=on)


def test_forecast_requires_opening_cash_not_assumed_zero(client, world):
    history(world, world.biz_a)
    r = client.get("/api/forecast", headers=world.h_a)
    assert r.status_code == 409 and r.json()["error"]["code"] == "opening_cash_required"


def test_opening_cash_must_be_month_end(client, world):
    r = client.put("/api/opening-cash", headers=world.h_a, json={"amount": "1000.00", "as_of_date": "2026-10-15"})
    assert r.status_code == 422
    ok = client.put("/api/opening-cash", headers=world.h_a, json={"amount": "1000.00", "as_of_date": "2026-10-31"})
    assert ok.status_code == 200


def test_forecast_moving_average_values(client, world):
    history(world, world.biz_a)
    set_opening(world, world.biz_a, "100000.00", "2026-10-31")
    f = client.get("/api/forecast?months=3", headers=world.h_a).json()
    assert f["periods"] == ["2026-11", "2026-12", "2027-01"]
    assert f["method"] == "3-month moving average" and f["months_of_history_used"] == 3
    first = f["values"][0]
    assert (first["predicted_income"], first["predicted_outflows"], first["predicted_closing_cash"]) == (50000.0, 20000.0, 130000.0)
    assert [v["predicted_closing_cash"] for v in f["values"]] == [130000.0, 160000.0, 190000.0]
    assert f["is_estimate"] is True and f["insufficient_data"] is False and f["warnings"] == []
    assert f["opening_cash_as_of"] == "2026-10-31" and "estimate" in f["disclaimer"].lower()
    assert any("estimate" in a.lower() for a in f["assumptions"])


def test_unpaid_expenses_and_unpaid_invoices_are_not_cash(client, world):
    history(world, world.biz_a)
    world.invoice(world.biz_a, "UNPAID", "sales", "999999.00")
    add_expense(world, world.biz_a, "88888.00", "2026-10-25")  # unpaid
    set_opening(world, world.biz_a)
    v = client.get("/api/forecast?months=1", headers=world.h_a).json()["values"][0]
    assert (v["predicted_income"], v["predicted_outflows"]) == (50000.0, 20000.0)


def test_payments_after_opening_cash_date_are_excluded(client, world):
    history(world, world.biz_a)
    sale = world.invoice(world.biz_a, "S-2", "sales", "500000.00")
    add_payment(world, world.biz_a, sale, "400000.00", "2026-11-05")  # after 2026-10-31
    set_opening(world, world.biz_a)
    v = client.get("/api/forecast?months=1", headers=world.h_a).json()["values"][0]
    assert v["predicted_income"] == 50000.0


def test_empty_months_count_as_zero(client, world):
    sale = world.invoice(world.biz_a, "S-1", "sales", "90000.00")
    add_payment(world, world.biz_a, sale, "30000.00", "2026-08-10")
    add_payment(world, world.biz_a, sale, "60000.00", "2026-10-10")   # September has nothing
    set_opening(world, world.biz_a)
    v = client.get("/api/forecast?months=1", headers=world.h_a).json()["values"][0]
    assert v["predicted_income"] == 30000.0  # (30000 + 0 + 60000) / 3


def test_short_history_is_flagged(client, world):
    sale = world.invoice(world.biz_a, "S-1", "sales", "90000.00")
    add_payment(world, world.biz_a, sale, "30000.00", "2026-09-10")
    add_payment(world, world.biz_a, sale, "60000.00", "2026-10-10")
    set_opening(world, world.biz_a)
    f = client.get("/api/forecast", headers=world.h_a).json()
    assert f["method"] == "2-month moving average" and any("2 month" in w for w in f["warnings"])


def test_no_history_reports_insufficient_data(client, world):
    set_opening(world, world.biz_a)
    f = client.get("/api/forecast", headers=world.h_a).json()
    assert f["insufficient_data"] is True and f["periods"] == [] and f["warnings"]


def test_forecast_isolated_between_businesses(client, world):
    history(world, world.biz_b)
    set_opening(world, world.biz_a)
    f = client.get("/api/forecast", headers=world.h_a).json()
    assert f["insufficient_data"] is True              # A sees none of B's history
    assert client.get("/api/forecast", headers=world.h_b).status_code == 409  # B never set opening cash


def test_forecast_parameter_validation(client, world):
    for q in ("months=0", "months=13", "window=0"):
        assert client.get(f"/api/forecast?{q}", headers=world.h_a).status_code == 422
