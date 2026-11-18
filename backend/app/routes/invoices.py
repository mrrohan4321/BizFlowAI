from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.auth import CurrentUser, get_business_id, get_current_user
from app.schemas.invoices import InvoiceConfirm, InvoiceUpdate
from app.services import invoices

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.post("/extract")
def extract(file: UploadFile = File(...), user: CurrentUser = Depends(get_current_user),
            business_id: str = Depends(get_business_id)):
    """Upload + AI extraction. Returns data for human review; NOTHING is saved as an invoice."""
    return invoices.extract_and_stage(business_id, user.id, file.filename, file.file)


@router.post("", status_code=201)
def confirm(body: InvoiceConfirm, user: CurrentUser = Depends(get_current_user),
            business_id: str = Depends(get_business_id)):
    return invoices.confirm_invoice(business_id, user.id, body)


@router.get("")
def list_(invoice_type: Optional[Literal["sales", "purchase"]] = None,
          status: Optional[Literal["unpaid", "partially_paid", "paid"]] = None,
          date_from: Optional[date] = None, date_to: Optional[date] = None, party: Optional[str] = Query(None, max_length=200),
          limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
          business_id: str = Depends(get_business_id)):
    return invoices.list_invoices(business_id, invoice_type, status, date_from, date_to, party, limit, offset)


@router.get("/{invoice_id}")
def get(invoice_id: UUID, business_id: str = Depends(get_business_id)):
    return invoices.get_invoice(business_id, str(invoice_id))


@router.patch("/{invoice_id}")
@router.put("/{invoice_id}")
def update(invoice_id: UUID, body: InvoiceUpdate, business_id: str = Depends(get_business_id)):
    return invoices.update_invoice(business_id, str(invoice_id), body)


@router.delete("/{invoice_id}", status_code=204)
def delete(invoice_id: UUID, business_id: str = Depends(get_business_id)):
    invoices.delete_invoice(business_id, str(invoice_id))
    return Response(status_code=204)
