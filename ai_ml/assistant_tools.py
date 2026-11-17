"""Approved assistant functions only. No LLM-generated SQL/code. Always scope by business_id."""


def get_receivables_summary(business_id: str) -> dict: raise NotImplementedError
def get_payables_summary(business_id: str) -> dict: raise NotImplementedError
def get_overdue_invoices(business_id: str) -> dict: raise NotImplementedError
def get_monthly_performance(business_id: str) -> dict: raise NotImplementedError
def get_cash_forecast(business_id: str) -> dict: raise NotImplementedError


TOOLS = {
    "get_receivables_summary": get_receivables_summary,
    "get_payables_summary": get_payables_summary,
    "get_overdue_invoices": get_overdue_invoices,
    "get_monthly_performance": get_monthly_performance,
    "get_cash_forecast": get_cash_forecast,
}
