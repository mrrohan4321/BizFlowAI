
"""Pydantic data models shared across the BizFlow AI/ML package.

These models define what valid data looks like. Pydantic checks the
data and raises an error when something is invalid, so bad values are
never accepted silently.
"""

import re
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

    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(BaseModel):
    """One problem found while extracting or validating an invoice."""

    field: str | None = None
    severity: Severity
    message: str


# --------------------------------------------------------------------------
# Invoice fields
# --------------------------------------------------------------------------
class InvoiceFields(BaseModel):
    """Structured fields extracted from one invoice.

    Every field is optional because an invoice may not contain it.
    Missing values stay None; we never invent values.
    """

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
        "subtotal",
        "tax_amount",
        "cgst",
        "sgst",
        "igst",
        "total_amount",
        mode="before",
    )
    @classmethod
    def clean_amount(cls, value: Any) -> Decimal | None:
        """Convert supported currency representations into finite Decimals.

        Examples:
            '₹1,23,456.78' -> Decimal('123456.78')
            'Rs. 12,500'    -> Decimal('12500')
            'INR 500'       -> Decimal('500')

        Empty values become None. Invalid or non-finite amounts are rejected.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            raise ValueError("a boolean is not a valid amount")

        if isinstance(value, (int, float, Decimal)):
            try:
                amount = Decimal(str(value))
            except InvalidOperation as exc:
                raise ValueError("invalid monetary amount") from exc

            if not amount.is_finite():
                raise ValueError("amount must be a finite number")

            return amount

        if not isinstance(value, str):
            raise ValueError(
                f"unsupported amount type: {type(value).__name__}"
            )

        cleaned = value.strip()

        if not cleaned:
            return None

        # Remove one recognized currency prefix.
        cleaned = re.sub(
            r"^(?:₹|Rs\.?|INR)\s*",
            "",
            cleaned,
            count=1,
            flags=re.IGNORECASE,
        ).strip()

        # Accept ungrouped digits, Indian comma grouping, or
        # international comma grouping. Reject malformed separators.
        valid_number = re.fullmatch(
            r"[+-]?(?:"
            r"\d+"
            r"|\d{1,3}(?:,\d{2})*,\d{3}"
            r"|\d{1,3}(?:,\d{3})+"
            r")(?:\.\d+)?",
            cleaned,
        )

        if not valid_number:
            raise ValueError(
                f"cannot read '{value}' as a valid monetary amount"
            )

        cleaned = cleaned.replace(",", "")

        try:
            amount = Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValueError(
                f"cannot read '{value}' as an amount"
            ) from exc

        if not amount.is_finite():
            raise ValueError("amount must be a finite number")

        return amount

    @field_validator("invoice_type", mode="before")
    @classmethod
    def clean_invoice_type(cls, value: Any) -> Any:
        """Accept values such as 'Sales' and ' PURCHASE '."""
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

    @field_validator(
        "invoice_number",
        "party_name",
        "gstin",
        mode="before",
    )
    @classmethod
    def clean_text(cls, value: Any) -> Any:
        """Trim spaces and convert empty strings into None."""
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("gstin")
    @classmethod
    def normalize_gstin(cls, value: str | None) -> str | None:
        """Normalize GSTIN to uppercase for consistent storage."""
        return value.upper() if value is not None else None


# --------------------------------------------------------------------------
# Invoice extraction result
# --------------------------------------------------------------------------
class InvoiceExtractionResult(BaseModel):
    """What extract_invoice() returns to the main application.

    The user must review this before anything is saved.
    """

    fields: InvoiceFields
    issues: list[ValidationIssue] = Field(default_factory=list)
    needs_review: bool = True
    source_file: str | None = None
    raw_text_preview: str | None = None


# --------------------------------------------------------------------------
# Forecast output
# --------------------------------------------------------------------------
class ForecastResult(BaseModel):
    """A cash-flow estimate for one future month."""

    forecast_period: str
    predicted_income: Decimal
    predicted_outflows: Decimal
    opening_cash: Decimal
    predicted_closing_cash: Decimal
    method: str
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
    tool_used: str | None = None
    data: dict[str, Any] | None = None
    insufficient_data: bool = False
