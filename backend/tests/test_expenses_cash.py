import uuid

EXP = {"category": "rent", "amount": "5000.00", "expense_date": "2026-11-01"}


def test_expense_defaults_to_unpaid(client, world):
    r = client.post("/api/expenses", json=EXP, headers=world.h_a)
    assert r.status_code == 201
    assert r.json()["payment_status"] == "unpaid" and r.json()["paid_date"] is None


def test_paid_expense_requires_paid_date(client, world):
    assert client.post("/api/expenses", json={**EXP, "payment_status": "paid"}, headers=world.h_a).status_code == 422
    ok = client.post("/api/expenses", json={**EXP, "payment_status": "paid", "paid_date": "2026-11-02"}, headers=world.h_a)
    assert ok.status_code == 201
    assert client.post("/api/expenses", json={**EXP, "paid_date": "2026-11-02"}, headers=world.h_a).status_code == 422


def test_negative_amount_rejected(client, world):
    assert client.post("/api/expenses", json={**EXP, "amount": "-1"}, headers=world.h_a).status_code == 422


def test_expense_list_filters_and_isolation(client, world):
    client.post("/api/expenses", json=EXP, headers=world.h_a)
    client.post("/api/expenses", json={**EXP, "category": "tea", "payment_status": "paid", "paid_date": "2026-11-02"},
                headers=world.h_a)
    client.post("/api/expenses", json=EXP, headers=world.h_b)
    assert len(client.get("/api/expenses", headers=world.h_a).json()["items"]) == 2
    assert len(client.get("/api/expenses?payment_status=paid", headers=world.h_a).json()["items"]) == 1
    assert len(client.get("/api/expenses?category=tea", headers=world.h_a).json()["items"]) == 1
    assert len(client.get("/api/expenses", headers=world.h_b).json()["items"]) == 1


def test_mark_expense_paid(client, world):
    eid = client.post("/api/expenses", json=EXP, headers=world.h_a).json()["id"]
    r = client.patch(f"/api/expenses/{eid}", json={"payment_status": "paid", "paid_date": "2026-11-03"}, headers=world.h_a)
    assert r.status_code == 200 and r.json()["payment_status"] == "paid"
    back = client.patch(f"/api/expenses/{eid}", json={"payment_status": "unpaid"}, headers=world.h_a)
    assert back.json()["paid_date"] is None
    assert client.patch(f"/api/expenses/{eid}", json={"payment_status": "paid"}, headers=world.h_a).status_code == 422


def test_cannot_update_other_business_expense(client, world):
    eid = client.post("/api/expenses", json=EXP, headers=world.h_b).json()["id"]
    r = client.patch(f"/api/expenses/{eid}", json={"category": "hacked"}, headers=world.h_a)
    assert r.status_code == 404
    assert client.get("/api/expenses", headers=world.h_b).json()["items"][0]["category"] == "rent"
    assert client.patch(f"/api/expenses/{uuid.uuid4()}", json={"notes": "x"}, headers=world.h_a).status_code == 404


def test_opening_cash_upsert_negative_and_isolation(client, world):
    body = {"amount": "25000.00", "as_of_date": "2026-10-31", "note": "bank"}
    assert client.put("/api/opening-cash", json=body, headers=world.h_a).status_code == 200
    client.put("/api/opening-cash", json={**body, "amount": "-100.00"}, headers=world.h_a)  # same date -> update
    items = client.get("/api/opening-cash", headers=world.h_a).json()["items"]
    assert len(items) == 1 and items[0]["amount"] == -100.0
    assert client.get("/api/opening-cash", headers=world.h_b).json()["items"] == []
