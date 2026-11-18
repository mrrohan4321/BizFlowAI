import logging
from datetime import datetime, timedelta, timezone

import psycopg2.errors
from psycopg2.extras import Json

from ai_ml.invoice_extraction import extract_invoice  # source of truth for OCR + extraction
from ai_ml.schemas import InvoiceFields, Severity
from ai_ml.validation import validate_invoice
from app import config
from app.db.database import get_connection, get_cursor
from app.errors import AppError
from app.services.payments import invoice_balance
from app.services.uploads import delete_stored, display_name, store_upload
from app.utils import serialize

log = logging.getLogger("bizflow")
_FIELDS = ("invoice_number", "invoice_type", "party_name", "invoice_date", "due_date", "subtotal", "tax_amount",
           "cgst", "sgst", "igst", "total_amount", "gstin", "notes")
_AI_FAIL_PREFIX = "Invoice extraction failed"


# ---------- extraction (nothing is saved to `invoices` here) ----------
def _cleanup_expired() -> None:
    try:
        with get_cursor() as cur:
            cur.execute("DELETE FROM invoice_extractions WHERE expires_at < now() RETURNING stored_file")
            for r in cur.fetchall():
                delete_stored(r["stored_file"])
    except Exception as exc:  # best effort, must never break an upload
        log.warning("extraction cleanup failed: %s", type(exc).__name__)


def extract_and_stage(business_id: str, user_id: str, filename: str | None, stream) -> dict:
    _cleanup_expired()
    rel, path = store_upload(business_id, filename, stream)
    try:
        try:
            result = extract_invoice(path)
        except RuntimeError as exc:  # OCR engine/page failure
            log.error("OCR runtime failure: %s", type(exc).__name__)
            raise AppError(503, "ocr_unavailable", "Text extraction is temporarily unavailable.")
        except (ValueError, FileNotFoundError, OSError) as exc:
            log.warning("OCR failed: %s", type(exc).__name__)
            raise AppError(422, "ocr_failed", "Could not read text from this file. Try a clearer scan.")
        fields = result.fields.model_dump(mode="json")
        issues = [i.model_dump(mode="json") for i in result.issues]
        ai_failed = (all(v is None for v in fields.values())
                     and any(i["severity"] == "error" and i["message"].startswith(_AI_FAIL_PREFIX) for i in issues))
        if ai_failed:  # keep internal error text server-side
            issues = [{"field": None, "severity": "error",
                       "message": "Automatic extraction failed. Please enter the invoice details manually."}]
        expires = datetime.now(timezone.utc) + timedelta(minutes=config.EXTRACTION_TTL_MINUTES)
        with get_cursor() as cur:
            cur.execute("INSERT INTO invoice_extractions (business_id, user_id, stored_file, original_filename, "
                        "extracted, issues, needs_review, expires_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                        "RETURNING id, expires_at",
                        (business_id, user_id, rel, display_name(filename), Json(fields), Json(issues), True, expires))
            row = cur.fetchone()
    except BaseException:
        delete_stored(rel)
        raise
    return {"extraction_id": str(row["id"]), "extraction_status": "ai_extraction_failed" if ai_failed else "ok",
            "extracted_fields": fields, "warnings": issues, "needs_review": True,
            "raw_text_preview": None if ai_failed else result.raw_text_preview,
            "expires_at": row["expires_at"].isoformat(), "saved": False}


# ---------- validation of user-confirmed data ----------
def _validate(values: dict) -> tuple[list[dict], str]:
    fields = InvoiceFields.model_validate({k: values.get(k) for k in InvoiceFields.model_fields})
    issues = validate_invoice(fields)
    if any(i.severity == Severity.ERROR for i in issues):
        raise AppError(422, "invalid_invoice", "Invoice data failed validation.",
                       [i.model_dump(mode="json") for i in issues])
    return ([i.model_dump(mode="json") for i in issues], "needs_review" if issues else "confirmed")


def _public(row: dict, payments: list) -> dict:
    out = serialize({k: v for k, v in row.items() if k not in ("file_path", "payment_amounts")})
    out["has_file"] = bool(row.get("file_path"))
    out.update(invoice_balance(row["total_amount"], payments))
    return out


def _duplicate() -> AppError:
    return AppError(409, "duplicate_invoice", "An invoice with this number and type already exists.")


# ---------- confirm (explicit save) ----------
def confirm_invoice(business_id: str, user_id: str, body) -> dict:
    if body.confirmed is not True:
        raise AppError(422, "confirmation_required", "Invoice must be explicitly confirmed to be saved.")
    values = body.model_dump(include=set(_FIELDS))
    warnings, review_status = _validate(values)
    stored = None
    try:
        with get_connection() as conn, conn.cursor() as cur:
            if body.extraction_id:
                cur.execute("SELECT * FROM invoice_extractions WHERE id = %s AND business_id = %s FOR UPDATE",
                            (str(body.extraction_id), business_id))
                ex = cur.fetchone()
                if ex is None:
                    raise AppError(404, "extraction_not_found", "Extraction not found.")
                if ex["consumed_at"] is not None:
                    raise AppError(409, "extraction_already_used", "This extraction was already saved.")
                cur.execute("SELECT now() > %s AS expired", (ex["expires_at"],))
                if cur.fetchone()["expired"]:
                    raise AppError(410, "extraction_expired", "This extraction expired. Please upload again.")
                stored = ex["stored_file"]
            try:
                cur.execute("INSERT INTO invoices (business_id, invoice_number, invoice_type, party_name, invoice_date, "
                            "due_date, subtotal, tax_amount, cgst, sgst, igst, total_amount, gstin, notes, file_path, "
                            "review_status) VALUES (%(b)s,%(invoice_number)s,%(invoice_type)s,%(party_name)s,"
                            "%(invoice_date)s,%(due_date)s,%(subtotal)s,%(tax_amount)s,%(cgst)s,%(sgst)s,%(igst)s,"
                            "%(total_amount)s,%(gstin)s,%(notes)s,%(f)s,%(r)s) RETURNING *",
                            {**values, "b": business_id, "f": stored, "r": review_status})
            except psycopg2.errors.UniqueViolation:
                raise _duplicate()
            row = cur.fetchone()
            if body.extraction_id:
                cur.execute("UPDATE invoice_extractions SET consumed_at = now() WHERE id = %s", (str(body.extraction_id),))
    except AppError:
        raise
    return {"invoice": _public(row, []), "warnings": warnings}


# ---------- read / update / delete ----------
_SELECT = ("SELECT i.*, COALESCE((SELECT array_agg(p.amount) FROM payments p WHERE p.invoice_id = i.id "
           "AND p.business_id = i.business_id), '{}') AS payment_amounts FROM invoices i WHERE i.business_id = %s")


def list_invoices(business_id, invoice_type=None, status=None, date_from=None, date_to=None, party=None,
                  limit=100, offset=0) -> dict:
    sql, args = _SELECT, [business_id]
    for clause, val in (("i.invoice_type = %s", invoice_type), ("i.invoice_date >= %s", date_from),
                        ("i.invoice_date <= %s", date_to)):
        if val:
            sql += f" AND {clause}"
            args.append(val)
    if party:
        sql += " AND i.party_name ILIKE %s"
        args.append("%" + party.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
    sql += " ORDER BY i.invoice_date DESC NULLS LAST, i.created_at DESC"
    with get_cursor() as cur:
        cur.execute(sql, args)
        items = [_public(r, r["payment_amounts"]) for r in cur.fetchall()]
    if status:  # status is computed by ai_ml, so filter after computing
        items = [i for i in items if i["status"] == status]
    return {"items": items[offset:offset + limit], "total": len(items)}


def _get_row(cur, business_id: str, invoice_id: str, lock=False) -> dict:
    cur.execute(_SELECT + " AND i.id = %s" + (" FOR UPDATE OF i" if lock else ""), (business_id, invoice_id))
    row = cur.fetchone()
    if row is None:
        raise AppError(404, "invoice_not_found", "Invoice not found.")
    return row


def get_invoice(business_id: str, invoice_id: str) -> dict:
    with get_cursor() as cur:
        row = _get_row(cur, business_id, invoice_id)
    return _public(row, row["payment_amounts"])


def update_invoice(business_id: str, invoice_id: str, body) -> dict:
    changes = body.model_dump(exclude_unset=True)
    with get_connection() as conn, conn.cursor() as cur:
        row = _get_row(cur, business_id, invoice_id, lock=True)
        merged = {**{k: row[k] for k in _FIELDS}, **changes}
        if merged["total_amount"] is None:
            raise AppError(422, "invalid_request", "total_amount cannot be empty.")
        warnings, review_status = _validate(merged)
        if "total_amount" in changes and row["payment_amounts"] and \
                invoice_balance(merged["total_amount"], row["payment_amounts"])["amount_paid"] > float(merged["total_amount"]):
            raise AppError(422, "total_below_payments", "Total cannot be lower than payments already recorded.")
        sets = ", ".join(f"{k} = %({k})s" for k in _FIELDS)
        try:
            cur.execute(f"UPDATE invoices SET {sets}, review_status = %(r)s, updated_at = now() "
                        "WHERE id = %(id)s AND business_id = %(b)s RETURNING *",
                        {**merged, "r": review_status, "id": invoice_id, "b": business_id})
        except psycopg2.errors.UniqueViolation:
            raise _duplicate()
        new = cur.fetchone()
    return {"invoice": _public(new, row["payment_amounts"]), "warnings": warnings}


def delete_invoice(business_id: str, invoice_id: str) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        row = _get_row(cur, business_id, invoice_id, lock=True)
        if row["payment_amounts"]:
            raise AppError(409, "invoice_has_payments", "Cannot delete an invoice that has payments recorded.")
        cur.execute("DELETE FROM invoices WHERE id = %s AND business_id = %s", (invoice_id, business_id))
    delete_stored(row["file_path"])
