import uuid


def pay(client, headers, invoice_id, amount, **kw):
    body = {"invoice_id": invoice_id, "amount": amount, "payment_date": "2026-11-05", **kw}
    return client.post("/api/payments", json=body, headers=headers)


def test_full_payment(client, world):
    inv = world.invoice(world.biz_a, total="1000.00")
    r = pay(client, world.h_a, inv, "1000.00", method="upi", reference="UTR1")
    assert r.status_code == 201
    j = r.json()
    assert j["invoice"]["status"] == "paid" and j["invoice"]["outstanding_amount"] == 0
    assert j["payment"]["reference"] == "UTR1"


def test_partial_then_multiple_payments(client, world):
    inv = world.invoice(world.biz_a, total="1000.00")
    r1 = pay(client, world.h_a, inv, "300.00").json()["invoice"]
    assert (r1["status"], r1["amount_paid"], r1["outstanding_amount"]) == ("partially_paid", 300.0, 700.0)
    r2 = pay(client, world.h_a, inv, "200.50").json()["invoice"]
    assert (r2["amount_paid"], r2["outstanding_amount"]) == (500.5, 499.5)
    r3 = pay(client, world.h_a, inv, "499.50").json()["invoice"]
    assert r3["status"] == "paid"
    assert len(client.get(f"/api/payments?invoice_id={inv}", headers=world.h_a).json()["items"]) == 3


def test_overpayment_rejected_and_nothing_saved(client, world):
    inv = world.invoice(world.biz_a, total="100.00")
    r = pay(client, world.h_a, inv, "100.01")
    assert r.status_code == 422 and r.json()["error"]["code"] == "overpayment"
    assert client.get("/api/payments", headers=world.h_a).json()["items"] == []


def test_overpayment_after_partial(client, world):
    inv = world.invoice(world.biz_a, total="100.00")
    assert pay(client, world.h_a, inv, "60").status_code == 201
    assert pay(client, world.h_a, inv, "50").status_code == 422


def test_invalid_amounts_rejected(client, world):
    inv = world.invoice(world.biz_a)
    for bad in ("0", "-5", "abc", "10.123", None):
        assert pay(client, world.h_a, inv, bad).status_code == 422, bad


def test_unknown_invoice_404(client, world):
    assert pay(client, world.h_a, str(uuid.uuid4()), "10").status_code == 404


def test_cannot_pay_other_business_invoice(client, world):
    inv_b = world.invoice(world.biz_b)
    r = pay(client, world.h_a, inv_b, "10")
    assert r.status_code == 404  # existence not leaked
    assert client.get("/api/payments", headers=world.h_b).json()["items"] == []


def test_business_id_in_body_is_rejected(client, world):
    inv = world.invoice(world.biz_a)
    r = pay(client, world.h_a, inv, "10", business_id=world.biz_b)
    assert r.status_code == 422


def test_list_is_isolated_by_business(client, world):
    ia, ib = world.invoice(world.biz_a), world.invoice(world.biz_b)
    pay(client, world.h_a, ia, "10")
    pay(client, world.h_b, ib, "20")
    a = client.get("/api/payments", headers=world.h_a).json()["items"]
    assert [p["amount"] for p in a] == [10.0]
    assert client.get(f"/api/payments?invoice_id={ib}", headers=world.h_a).json()["items"] == []


def test_date_filter(client, world):
    inv = world.invoice(world.biz_a)
    pay(client, world.h_a, inv, "10", payment_date="2026-10-01")
    pay(client, world.h_a, inv, "20", payment_date="2026-11-01")
    items = client.get("/api/payments?date_from=2026-11-01", headers=world.h_a).json()["items"]
    assert [p["amount"] for p in items] == [20.0]
