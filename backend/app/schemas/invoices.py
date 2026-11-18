from datetime import date
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Amount = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InvoiceConfirm(_Strict):
    """What the user submits AFTER reviewing/correcting extracted data. Nothing is saved without confirmed=true."""
    confirmed: bool
    extraction_id: Optional[UUID] = None       # omit for manual entry (no file)
    invoice_number: str = Field(min_length=1, max_length=100)
    invoice_type: Literal["sales", "purchase"]
    party_name: Optional[str] = Field(default=None, max_length=200)
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[Decimal] = Amount
    tax_amount: Optional[Decimal] = Amount
    cgst: Optional[Decimal] = Amount
    sgst: Optional[Decimal] = Amount
    igst: Optional[Decimal] = Amount
    total_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    gstin: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = Field(default=None, max_length=1000)


class InvoiceUpdate(_Strict):
    invoice_number: Optional[str] = Field(default=None, min_length=1, max_length=100)
    invoice_type: Optional[Literal["sales", "purchase"]] = None
    party_name: Optional[str] = Field(default=None, max_length=200)
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[Decimal] = Amount
    tax_amount: Optional[Decimal] = Amount
    cgst: Optional[Decimal] = Amount
    sgst: Optional[Decimal] = Amount
    igst: Optional[Decimal] = Amount
    total_amount: Optional[Decimal] = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    gstin: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = Field(default=None, max_length=1000)
