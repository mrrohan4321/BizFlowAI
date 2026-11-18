"""Finance assistant: backend fetches ONLY this business's records, ai_ml selects a tool and explains."""
import logging
from datetime import date

from app.db.database import get_cursor
from app.errors import AppError
from app.services.analytics import cash_history, latest_opening_cash, load_records

log = logging.getLogger("bizflow")
_FOLLOW_UPS = {
    "get_receivables_summary": "Which customer invoices are overdue?",
    "get_payables_summary": "Which supplier bills are overdue?",
    "get_overdue_invoices": "How much do customers still owe me in total?",
    "get_monthly_performance": "What is my expected cash flow for the next 3 months?",
    "get_cash_forecast": "How did my business perform in recent months?",
}


def chat(business_id: str, question: str) -> dict:
    from ai_ml import assistant as ai  # lazy: keeps app start-up independent of the Groq SDK

    with get_cursor() as cur:
        invoices, payments, expenses = load_records(cur, business_id)
        opening = latest_opening_cash(cur, business_id)
        history = cash_history(cur, business_id, up_to=opening["as_of_date"] if opening else None)
    try:
        res = ai.answer_finance_question(
            question=question, business_id=business_id, invoices=invoices, payments=payments, expenses=expenses,
            monthly_history=history, opening_cash=float(opening["amount"]) if opening else None,
            today=date.today())
    except RuntimeError:
        log.error("assistant unavailable: Groq is not configured")
        raise AppError(503, "ai_not_configured", "The AI assistant is not configured on the server.")
    except (ValueError, TypeError) as exc:
        if "Opening cash is required" in str(exc):
            return {"question": question, "tool_used": None, "data": None, "data_used": None, "insufficient_data": True,
                    "answer": "I need your opening cash balance to forecast cash flow. Please set it first, then ask again.",
                    "follow_up": "How much do customers owe me?"}
        log.warning("assistant failed: %s", type(exc).__name__)
        raise AppError(502, "assistant_failed", "The assistant could not complete this request. Please try again.")
    out = res.model_dump(mode="json")
    out["data_used"] = out["data"]            # name used in API-notes.md
    out["follow_up"] = _FOLLOW_UPS.get(res.tool_used)
    return out
