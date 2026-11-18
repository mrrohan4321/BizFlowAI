import io
import uuid
from decimal import Decimal

import pytest

from ai_ml.schemas import InvoiceExtractionResult, InvoiceFields, Severity, ValidationIssue
from app import config

PDF = b"%PDF-1.4\n" + b"x" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 100
JPG = b"\xff\xd8\xff\xe0" + b"x" * 100

GOOD = {"confirmed": True, "invoice_number": "INV-1", "invoice_type": "sales", "party_name": "ABC",
        "invoice_date": "2026-10-01", "due_date": "2026-10-31", "subtotal": "1000.00", "tax_amount": "180.00",
        "total_amount": "1180.00"}


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path)
    return tmp_path


def fake_result(monkeypatch, fields=None, issues=None):
    res = InvoiceExtractionResult(
        fields=InvoiceFields(**(fields if fields is not None else
                                {"invoice_number": "INV-9", "invoice_type": "sales", "party_name": "ABC",
                                 "total_amount": "1180.00"})),
        issues=issues or [], raw_text_preview="Invoice INV-9")
    monkeypatch.setattr("app.services.invoices.extract_invoice", lambda path: res)


def upload(client, headers, data=PDF, name="inv.pdf"):
    return client.post("/api/invoices/extract", files={"file": (name, io.BytesIO(data))}, headers=headers)


def files_in(d):
    return [p for p in d.rglob("*") if p.is_file()]


def count_invoices(client, h):
    return client.get("/api/invoices", headers=h).json()["total"]


# ---------- upload ----------
@pytest.mark.parametrize("data,name", [(PDF, "a.pdf"), (PNG, "a.png"), (JPG, "a.jpg"), (JPG, "a.JPEG")])
def test_valid_uploads_extract_but_do_not_save(client, world, monkeypatch, upload_dir, data, name):
    fake_result(monkeypatch)
    r = upload(client, world.h_a, data, name)
    assert r.status_code == 200
    j = r.json()
    assert j["saved"] is False and j["extraction_status"] == "ok" and j["needs_review"] is True
    assert j["extracted_fields"]["invoice_number"] == "INV-9" and j["extraction_id"]
    assert count_invoices(client, world.h_a) == 0          # NOT persisted
    assert len(files_in(upload_dir)) == 1


def test_unsupported_types_rejected(client, world, monkeypatch, upload_dir):
    fake_result(monkeypatch)
    assert upload(client, world.h_a, b"MZ" + b"x" * 50, "evil.exe").status_code == 415
    assert upload(client, world.h_a, b"hello world, not a pdf", "fake.pdf").status_code == 415  # magic mismatch
    assert upload(client, world.h_a, PNG, "pic.pdf").status_code == 415
    assert files_in(upload_dir) == []


def test_oversized_upload_rejected_and_removed(client, world, monkeypatch, upload_dir):
    fake_result(monkeypatch)
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1000)
    r = upload(client, world.h_a, PDF + b"y" * 2000)
    assert r.status_code == 413 and r.json()["error"]["code"] == "file_too_large"
    assert files_in(upload_dir) == []


def test_unsafe_filename_is_never_used_as_path(client, world, monkeypatch, upload_dir):
    fake_result(monkeypatch)
    r = upload(client, world.h_a, PDF, "../../../etc/evil.pdf")
    assert r.status_code == 200
    stored = files_in(upload_dir)
    assert len(stored) == 1 and upload_dir in stored[0].parents
    assert stored[0].parent.name == world.biz_a and "evil" not in stored[0].name


def test_unauthenticated_upload(client):
    assert client.post("/api/invoices/extract", files={"file": ("a.pdf", io.BytesIO(PDF))}).status_code == 401


def test_ocr_failure_cleans_up(client, world, monkeypatch, upload_dir):
    def boom(path):
        raise ValueError("secret internal detail")
    monkeypatch.setattr("app.services.invoices.extract_invoice", boom)
    r = upload(client, world.h_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "ocr_failed"
    assert "secret" not in r.text and files_in(upload_dir) == []


def test_ocr_engine_unavailable(client, world, monkeypatch):
    def boom(path):
        raise RuntimeError("engine missing")
    monkeypatch.setattr("app.services.invoices.extract_invoice", boom)
    assert upload(client, world.h_a).status_code == 503


def test_ai_failure_is_distinct_and_hides_details(client, world, monkeypatch):
    res = InvoiceExtractionResult(fields=InvoiceFields(), raw_text_preview="text", issues=[
        ValidationIssue(severity=Severity.ERROR, message="Invoice extraction failed: gsk_SECRET timeout")])
    monkeypatch.setattr("app.services.invoices.extract_invoice", lambda p: res)
    j = upload(client, world.h_a).json()
    assert j["extraction_status"] == "ai_extraction_failed" and "gsk_SECRET" not in str(j)
    assert j["raw_text_preview"] is None


def test_validation_warnings_returned(client, world, monkeypatch):
    fake_result(monkeypatch, fields={"invoice_type": "sales"},
                issues=[ValidationIssue(field="total_amount", severity=Severity.WARNING, message="total_amount is missing.")])
    j = upload(client, world.h_a).json()
    assert j["warnings"][0]["field"] == "total_amount"


# ---------- confirm ----------
def stage(client, world, monkeypatch, headers=None):
    fake_result(monkeypatch)
    return upload(client, headers or world.h_a).json()["extraction_id"]


def test_confirm_saves_only_with_explicit_confirmation(client, world, monkeypatch):
    ex = stage(client, world, monkeypatch)
    r = client.post("/api/invoices", json={**GOOD, "confirmed": False, "extraction_id": ex}, headers=world.h_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "confirmation_required"
    assert count_invoices(client, world.h_a) == 0
    r = client.post("/api/invoices", json={**GOOD, "extraction_id": ex}, headers=world.h_a)
    assert r.status_code == 201
    inv = r.json()["invoice"]
    assert inv["status"] == "unpaid" and inv["outstanding_amount"] == 1180.0 and inv["has_file"] is True
    assert "file_path" not in inv and inv["review_status"] == "confirmed"
    assert count_invoices(client, world.h_a) == 1


def test_extraction_is_single_use(client, world, monkeypatch):
    ex = stage(client, world, monkeypatch)
    assert client.post("/api/invoices", json={**GOOD, "extraction_id": ex}, headers=world.h_a).status_code == 201
    r = client.post("/api/invoices", json={**GOOD, "invoice_number": "INV-2", "extraction_id": ex}, headers=world.h_a)
    assert r.status_code == 409 and r.json()["error"]["code"] == "extraction_already_used"


def test_expired_extraction(client, world, monkeypatch):
    ex = stage(client, world, monkeypatch)
    with world.get_cursor() as cur:
        cur.execute("UPDATE invoice_extractions SET expires_at = now() - interval '1 minute'")
    assert client.post("/api/invoices", json={**GOOD, "extraction_id": ex}, headers=world.h_a).status_code == 410


def test_cannot_confirm_other_business_extraction(client, world, monkeypatch):
    ex = stage(client, world, monkeypatch, world.h_b)
    r = client.post("/api/invoices", json={**GOOD, "extraction_id": ex}, headers=world.h_a)
    assert r.status_code == 404 and count_invoices(client, world.h_a) == 0


def test_manual_entry_without_extraction(client, world):
    r = client.post("/api/invoices", json=GOOD, headers=world.h_a)
    assert r.status_code == 201 and r.json()["invoice"]["has_file"] is False


def test_warnings_keep_invoice_in_needs_review(client, world):
    r = client.post("/api/invoices", json={"confirmed": True, "invoice_number": "X1", "invoice_type": "sales",
                                           "total_amount": "500.00"}, headers=world.h_a)
    assert r.status_code == 201 and r.json()["invoice"]["review_status"] == "needs_review" and r.json()["warnings"]


def test_inconsistent_totals_stay_reviewable(client, world):
    bad = {**GOOD, "subtotal": "100.00", "tax_amount": "10.00", "total_amount": "999.00"}
    r = client.post("/api/invoices", json=bad, headers=world.h_a)
    assert r.status_code == 201  # ai_ml flags this as a WARNING: saved, but stays reviewable
    assert r.json()["invoice"]["review_status"] == "needs_review"
    assert "does not match" in r.json()["warnings"][0]["message"]


def test_duplicate_invoice_number_conflict_but_allowed_across_business_and_type(client, world):
    assert client.post("/api/invoices", json=GOOD, headers=world.h_a).status_code == 201
    assert client.post("/api/invoices", json=GOOD, headers=world.h_a).status_code == 409
    assert client.post("/api/invoices", json={**GOOD, "invoice_type": "purchase"}, headers=world.h_a).status_code == 201
    assert client.post("/api/invoices", json=GOOD, headers=world.h_b).status_code == 201


def test_confirm_rejects_business_id_and_bad_input(client, world):
    assert client.post("/api/invoices", json={**GOOD, "business_id": world.biz_b}, headers=world.h_a).status_code == 422
    assert client.post("/api/invoices", json={**GOOD, "total_amount": "-5"}, headers=world.h_a).status_code == 422
    assert client.post("/api/invoices", json={**GOOD, "invoice_type": "refund"}, headers=world.h_a).status_code == 422


# ---------- list / get / update / delete ----------
def test_list_filters_and_isolation(client, world):
    a_sales = world.invoice(world.biz_a, "S1", "sales", "1000.00")
    world.invoice(world.biz_a, "P1", "purchase", "500.00")
    world.invoice(world.biz_b, "S9", "sales", "999.00")
    client.post("/api/payments", json={"invoice_id": a_sales, "amount": "400", "payment_date": "2026-11-01"}, headers=world.h_a)
    g = lambda q="": client.get("/api/invoices" + q, headers=world.h_a).json()
    assert g()["total"] == 2
    assert [i["invoice_number"] for i in g("?invoice_type=purchase")["items"]] == ["P1"]
    assert [i["status"] for i in g("?status=partially_paid")["items"]] == ["partially_paid"]
    assert g("?status=paid")["total"] == 0
    assert g("?party=par")["total"] == 2 and g("?party=zzz")["total"] == 0
    assert g("?date_from=2026-10-02")["total"] == 0
    assert g("?party=%25")["total"] == 0                       # wildcard is escaped, not injected


def test_get_invoice_with_balance_and_cross_business_404(client, world):
    inv = world.invoice(world.biz_a, total="1000.00")
    client.post("/api/payments", json={"invoice_id": inv, "amount": "250", "payment_date": "2026-11-01"}, headers=world.h_a)
    j = client.get(f"/api/invoices/{inv}", headers=world.h_a).json()
    assert (j["amount_paid"], j["outstanding_amount"], j["status"]) == (250.0, 750.0, "partially_paid")
    assert client.get(f"/api/invoices/{inv}", headers=world.h_b).status_code == 404
    assert client.get(f"/api/invoices/{uuid.uuid4()}", headers=world.h_a).status_code == 404


def test_update_invoice_and_ownership(client, world):
    inv = world.invoice(world.biz_a, total="1000.00")
    r = client.patch(f"/api/invoices/{inv}", json={"party_name": "New Name", "notes": "n"}, headers=world.h_a)
    assert r.status_code == 200 and r.json()["invoice"]["party_name"] == "New Name"
    r = client.patch(f"/api/invoices/{inv}", json={"party_name": "Hack"}, headers=world.h_b)
    assert r.status_code == 404
    assert client.get(f"/api/invoices/{inv}", headers=world.h_a).json()["party_name"] == "New Name"
    assert client.patch(f"/api/invoices/{inv}", json={"business_id": world.biz_b}, headers=world.h_a).status_code == 422


def test_cannot_lower_total_below_payments(client, world):
    inv = world.invoice(world.biz_a, total="1000.00")
    client.post("/api/payments", json={"invoice_id": inv, "amount": "800", "payment_date": "2026-11-01"}, headers=world.h_a)
    r = client.patch(f"/api/invoices/{inv}", json={"total_amount": "500.00"}, headers=world.h_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "total_below_payments"


def test_delete_ownership_and_payments_guard(client, world):
    inv = world.invoice(world.biz_a)
    assert client.delete(f"/api/invoices/{inv}", headers=world.h_b).status_code == 404
    assert client.get(f"/api/invoices/{inv}", headers=world.h_a).status_code == 200
    client.post("/api/payments", json={"invoice_id": inv, "amount": "10", "payment_date": "2026-11-01"}, headers=world.h_a)
    r = client.delete(f"/api/invoices/{inv}", headers=world.h_a)
    assert r.status_code == 409 and r.json()["error"]["code"] == "invoice_has_payments"
    inv2 = world.invoice(world.biz_a, "INV-2")
    assert client.delete(f"/api/invoices/{inv2}", headers=world.h_a).status_code == 204
    assert client.get(f"/api/invoices/{inv2}", headers=world.h_a).status_code == 404


def test_delete_removes_stored_file(client, world, monkeypatch, upload_dir):
    ex = stage(client, world, monkeypatch)
    inv = client.post("/api/invoices", json={**GOOD, "extraction_id": ex}, headers=world.h_a).json()["invoice"]["id"]
    assert len(files_in(upload_dir)) == 1
    client.delete(f"/api/invoices/{inv}", headers=world.h_a)
    assert files_in(upload_dir) == []
