from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_business_id
from app.errors import AppError
from app.services import analytics

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics/summary")
def summary(date_from: Optional[date] = None, date_to: Optional[date] = None,
            business_id: str = Depends(get_business_id)):
    """sales_total, expense_total, receivables, payables, operating_surplus_estimate (computed by ai_ml)."""
    if date_from and date_to and date_from > date_to:
        raise AppError(422, "invalid_request", "date_from must not be after date_to.")
    return analytics.summary(business_id, date_from, date_to)


@router.get("/analytics/monthly")
def monthly(business_id: str = Depends(get_business_id)):
    return analytics.monthly(business_id)


@router.get("/analytics/overdue")
@router.get("/payments/overdue")  # path used in API-notes.md
def overdue(as_of: Optional[date] = None, business_id: str = Depends(get_business_id)):
    return analytics.overdue(business_id, as_of)


@router.get("/forecast")
def forecast(months: int = Query(3, ge=1, le=12), window: int = Query(3, ge=1, le=12),
             business_id: str = Depends(get_business_id)):
    return analytics.forecast(business_id, months, window)
