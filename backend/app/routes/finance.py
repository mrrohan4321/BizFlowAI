from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth import get_business_id
from app.schemas.finance import ExpenseCreate, ExpenseUpdate, OpeningCashSet, PaymentCreate
from app.services import cash, expenses, payments

router = APIRouter(prefix="/api", tags=["finance"])


@router.post("/payments", status_code=201)
def create_payment(body: PaymentCreate, business_id: str = Depends(get_business_id)):
    return payments.record_payment(business_id, body)


@router.get("/payments")
def get_payments(invoice_id: Optional[UUID] = None, date_from: Optional[date] = None, date_to: Optional[date] = None,
                 limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                 business_id: str = Depends(get_business_id)):
    return {"items": payments.list_payments(business_id, invoice_id, date_from, date_to, limit, offset)}


@router.post("/expenses", status_code=201)
def create_expense(body: ExpenseCreate, business_id: str = Depends(get_business_id)):
    return expenses.create_expense(business_id, body)


@router.get("/expenses")
def get_expenses(category: Optional[str] = None, payment_status: Optional[Literal["unpaid", "paid"]] = None,
                 date_from: Optional[date] = None, date_to: Optional[date] = None,
                 limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                 business_id: str = Depends(get_business_id)):
    return {"items": expenses.list_expenses(business_id, category, payment_status, date_from, date_to, limit, offset)}


@router.patch("/expenses/{expense_id}")
def patch_expense(expense_id: UUID, body: ExpenseUpdate, business_id: str = Depends(get_business_id)):
    return expenses.update_expense(business_id, str(expense_id), body)


@router.put("/opening-cash")
def put_opening_cash(body: OpeningCashSet, business_id: str = Depends(get_business_id)):
    return cash.set_opening_cash(business_id, body)


@router.get("/opening-cash")
def get_opening_cash(business_id: str = Depends(get_business_id)):
    return {"items": cash.list_opening_cash(business_id)}
