from datetime import date, timedelta
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Decimal


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)  # business_id etc. are rejected


class PaymentCreate(_Strict):
    invoice_id: UUID
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    payment_date: date
    method: Optional[str] = Field(default=None, max_length=50)
    reference: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = Field(default=None, max_length=1000)


class ExpenseCreate(_Strict):
    category: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    expense_date: date
    description: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=1000)
    payment_status: Literal["unpaid", "paid"] = "unpaid"
    paid_date: Optional[date] = None

    @model_validator(mode="after")
    def _paid_consistency(self):
        if self.payment_status == "paid" and self.paid_date is None:
            raise ValueError("paid_date is required when payment_status is 'paid'")
        if self.payment_status == "unpaid" and self.paid_date is not None:
            raise ValueError("paid_date must be empty when payment_status is 'unpaid'")
        return self


class ExpenseUpdate(_Strict):
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=1000)
    payment_status: Optional[Literal["unpaid", "paid"]] = None
    paid_date: Optional[date] = None


class OpeningCashSet(_Strict):
    amount: Decimal = Field(max_digits=14, decimal_places=2)  # may be negative (overdraft)
    as_of_date: date  # last day of a month: the forecast starts the month after it
    note: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _month_end(self):
        if (self.as_of_date + timedelta(days=1)).day != 1:
            raise ValueError("as_of_date must be the last day of a month (e.g. 2026-10-31)")
        return self
