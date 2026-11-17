"""LLM structured extraction (Groq). Missing fields stay None - never guess."""
from datetime import date
from typing import Optional
from pydantic import BaseModel


class ExtractedInvoice(BaseModel):
    invoice_number: Optional[str] = None
    invoice_type: Optional[str] = None  # 'sales' | 'purchase'
    party_name: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None


def extract_invoice_fields(raw_text: str) -> ExtractedInvoice:
    """Send OCR text to LLM with strict JSON schema; validate with Pydantic."""
    raise NotImplementedError
