"""Pydantic data models shared across the BizFlow AI/ML package.

These models define what valid data looks like. Pydantic checks the
data and raises an error when something is invalid, so bad values are
never accepted silently.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --------------------------------------------------------------------------
# Warnings
# --------------------------------------------------------------------------
class Severity(str, Enum):
    """How serious a validation message is."""

    ERROR = "error"      # something is clearly wrong
    WARNING = "warning"  # suspicious or missing, needs human review


class ValidationIssue(BaseModel):
    """One problem found while extracting or validating an invoice."""

    field: str | None = None  # which field it is about, e.g. "total_amount"
    severity: Severity
    message: str


# --------------------------------------------------------------------------
# Invoice fields
# --------------------------------------------------------------------------
class InvoiceFields(BaseModel):
    """The structured fields extracted from one invoice.

    Every field is optional because an invoice may not contain it.
    A missing value stays None; we never invent values.
    """

    # Ignore any extra keys the LLM might add.
    model_config = ConfigDict(extra="ignore")

    invoice_number: str | None = None
    invoice_type: Literal["sales", "purchase"] | None = None
    party_name: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    subtotal: Decimal | None = None
    tax_amount: Decimal | None = None
    cgst: Decimal | None = None
    sgst: Decimal | None = None
    igst: Decimal | None = None
    total_amount: Decimal | None = None
    gstin: str | None = None

    @field_validator(
        "subtotal", "tax_amount", "cgst", "sgst", "igst", "total_amount",
        mode="before",
    )
    @classmethod
    def clean_amount(cls, value: Any) -> Decimal | None:
        """Turn things like '₹30,000.50' or 30000 into a Decimal.

        Empty strings and None become None. Text that cannot be read as
        a number raises an error instead of being guessed.
        """
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("a boolean is not a valid amount")
        if isinstance(value, (int, float, Decimal)):
            # str() first so floats do not carry binary rounding noise.
            return Decimal(str(value))
        if isinstance(value, str):
            cleaned = (
                value.replace("₹", "").replace("Rs.", "").replace("Rs", "")
                .replace(",", "").strip()
            )
            if cleaned == "":
                return None
            try:
                return Decimal(cleaned)
            except InvalidOperation:
                raise ValueError(f"cannot read '{value}' as an amount")
        raise ValueError(f"unsupported amount type: {type(value).__name__}")

    @field_validator("invoice_type", mode="before")
    @classmethod
    def clean_invoice_type(cls, value: Any) -> Any:
        """Accept 'Sales' or ' PURCHASE '; anything else must be rejected."""
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

    @field_validator(
        "invoice_number", "party_name", "gstin", mode="before"
    )
    @classmethod
    def clean_text(cls, value: Any) -> Any:
        """Trim spaces; turn empty strings into None."""
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


# --------------------------------------------------------------------------
# Invoice extraction result
# --------------------------------------------------------------------------
class InvoiceExtractionResult(BaseModel):
    """What extract_invoice() returns to the main application.

    The user must review this before anything is saved.
    """

    fields: InvoiceFields
    issues: list[ValidationIssue] = Field(default_factory=list)
    needs_review: bool = True  # always True: a human must confirm
    source_file: str | None = None
    raw_text_preview: str | None = None  # first part of the OCR text


# --------------------------------------------------------------------------
# Forecast output
# --------------------------------------------------------------------------
class ForecastResult(BaseModel):
    """A cash-flow estimate for one future month."""

    forecast_period: str  # e.g. "December 2026"
    predicted_income: Decimal
    predicted_outflows: Decimal
    opening_cash: Decimal
    predicted_closing_cash: Decimal
    method: str  # e.g. "3-month moving average"
    months_of_history_used: int
    disclaimer: str = "This is an estimate based on historical records."
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Assistant response
# --------------------------------------------------------------------------
class AssistantResponse(BaseModel):
    """What the finance assistant returns for one question."""

    question: str
    answer: str
    tool_used: str | None = None  # which approved function was called
    data: dict[str, Any] | None = None  # the real calculated result
    insufficient_data: bool = False