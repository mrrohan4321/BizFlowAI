
"""Groq-powered finance assistant for BizFlowAI.

Groq selects an approved tool and explains its result.
All financial calculations are performed by deterministic Python functions.
The backend must supply data already scoped to the authenticated business.
"""

import json
import logging
from datetime import date
from typing import Any

from groq import APIError, Groq

from . import config
from .assistant_tools import TOOLS
from .schemas import AssistantResponse

logger = logging.getLogger(__name__)


TOOL_SELECTION_PROMPT = """
You are the tool selector for BizFlowAI, a small-business finance assistant.

Choose exactly ONE tool from this approved list:

1. get_receivables_summary
   Use when the user asks about money customers owe, outstanding customer
   payments, or total receivables.

2. get_payables_summary
   Use when the user asks about money the business owes suppliers,
   outstanding supplier payments, or total payables.

3. get_overdue_invoices
   Use when the user asks about overdue invoices, late payments,
   or invoices past their due date.

4. get_monthly_performance
   Use when the user asks about historical monthly income, expenses,
   outflows, or net cash movement.

5. get_cash_forecast
   Use when the user asks about future cash flow, predicted income,
   predicted outflows, or future closing cash.

If the question does not match any approved tool, select null.

Return ONLY a JSON object in this exact format:
{"tool_name": "approved_tool_name"}

For unsupported questions:
{"tool_name": null}

Never invent a tool name. Do not provide explanations.
"""


ANSWER_PROMPT = """
You are BizFlowAI's finance assistant.

Explain the supplied Python-calculated financial result in clear,
simple language suitable for a small-business owner.

Important rules:

1. Use ONLY the supplied tool result.
2. Never invent, estimate, or modify financial figures.
3. Never invent a currency, currency symbol, or currency code.
4. Only display a currency symbol or code if the supplied tool result
   explicitly contains that currency information.
5. If no currency is specified, display amounts as plain numbers
   without any currency symbol or currency name.
6. Do not assume that a business uses USD, INR, or any other currency
   based on its location, name, or other contextual clues.
7. Never convert an amount into another currency.
8. Never change the numerical value calculated by Python.
9. Do not claim that a payment was received unless the data says so.
10. Clearly distinguish receivables, payables, expenses, and cash flow.
11. Mention when a forecast is an estimate based on historical records.
12. If the result contains no records, explain that clearly.
13. Do not provide SQL, code, or imaginary database information.
14. Keep the answer concise and directly address the question.

Accuracy is more important than presentation.
If the supplied data does not specify something, do not guess it.
"""


def _get_client() -> Groq:
    """Create the Groq client using the project's central configuration."""
    return Groq(
        api_key=config.require_groq_api_key(),
        timeout=config.GROQ_TIMEOUT_SECONDS,
    )


def _service_unavailable_response(question: str) -> AssistantResponse:
    """Return a safe response when Groq is unavailable."""
    return AssistantResponse(
        question=question,
        answer=(
            "The AI service is temporarily unavailable. "
            "Please try again shortly."
        ),
        tool_used=None,
        data=None,
        insufficient_data=True,
    )


def _select_tool(client: Groq, question: str) -> str | None:
    """Ask Groq to select one approved tool."""
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": TOOL_SELECTION_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise ValueError(
            "Groq returned an invalid tool-selection response."
        ) from exc

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Groq returned an empty tool-selection response.")

    try:
        selection = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Groq returned invalid JSON during tool selection."
        ) from exc

    if not isinstance(selection, dict):
        raise ValueError("Tool selection must be a JSON object.")

    if set(selection.keys()) != {"tool_name"}:
        raise ValueError(
            "Tool selection must contain only the tool_name field."
        )

    tool_name = selection["tool_name"]

    if tool_name is None:
        return None

    if not isinstance(tool_name, str) or tool_name not in TOOLS:
        raise ValueError("Groq selected a tool that is not approved.")

    return tool_name


def _build_tool_arguments(
    tool_name: str,
    business_id: str,
    invoices: list[dict] | None = None,
    payments: list[dict] | None = None,
    expenses: list[dict] | None = None,
    monthly_history: list[dict] | None = None,
    opening_cash: float | None = None,
    today: date | None = None,
    forecast_months: int = 3,
    forecast_window: int = 12,
) -> dict[str, Any]:
    """Build fixed arguments for an approved financial tool."""

    if tool_name == "get_receivables_summary":
        if invoices is None:
            raise ValueError("Invoice data must be supplied.")

        if payments is None:
            raise ValueError("Payment data must be supplied.")

        return {
            "business_id": business_id,
            "invoices": invoices,
            "payments": payments,
        }

    if tool_name == "get_payables_summary":
        if invoices is None:
            raise ValueError("Invoice data must be supplied.")

        if payments is None:
            raise ValueError("Payment data must be supplied.")

        return {
            "business_id": business_id,
            "invoices": invoices,
            "payments": payments,
        }

    if tool_name == "get_overdue_invoices":
        if invoices is None:
            raise ValueError("Invoice data was not supplied.")

        if payments is None:
            raise ValueError("Payment data was not supplied.")

        return {
            "business_id": business_id,
            "invoices": invoices,
            "payments": payments,
            "today": today,
        }

    if tool_name == "get_monthly_performance":
        if monthly_history is None:
            raise ValueError("Monthly financial history was not supplied.")

        return {
            "business_id": business_id,
            "monthly_history": monthly_history,
        }

    if tool_name == "get_cash_forecast":
        if monthly_history is None:
            raise ValueError("Monthly financial history was not supplied.")

        if opening_cash is None:
            raise ValueError(
                "Opening cash is required to generate a cash-flow forecast."
            )

        return {
            "business_id": business_id,
            "monthly_history": monthly_history,
            "opening_cash": opening_cash,
            "forecast_months": forecast_months,
            "window": forecast_window,
        }

    raise ValueError("Unsupported assistant tool.")


def _make_answer(
    client: Groq,
    question: str,
    tool_name: str,
    tool_result: dict,
) -> str:
    """Convert a real Python tool result into a natural-language answer."""
    result_json = json.dumps(
        tool_result,
        default=str,
        ensure_ascii=False,
    )

    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": ANSWER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"User question:\n{question}\n\n"
                    f"Approved tool used: {tool_name}\n\n"
                    f"Python-calculated result:\n{result_json}"
                ),
            },
        ],
        temperature=0,
    )

    try:
        answer = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise ValueError(
            "Groq returned an invalid assistant answer."
        ) from exc

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Groq returned an empty assistant answer.")

    return answer.strip()


def _fallback_answer(question: str) -> str:
    """Handle greetings, capability questions, and unsupported requests."""
    normalized = " ".join(
        question.lower().strip().rstrip("?!.,").split()
    )

    # Handle common greetings.
    greetings = {
        "hi",
        "hello",
        "hey",
        "hi there",
        "hello there",
        "hey there",
        "good morning",
        "good afternoon",
        "good evening",
    }

    if normalized in greetings:
        return (
            "Hello! I'm BizFlowAI's finance assistant. "
            "I can help you understand your business finances. "
            "You can ask me about receivables, payables, overdue invoices, "
            "monthly performance, or cash-flow forecasts."
        )

    # Handle questions about the assistant's capabilities.
    help_phrases = (
        "how can you help",
        "how can u help",
        "how can i use you",
        "what can you do",
        "what can u do",
        "what do you do",
        "what can i ask",
        "your capabilities",
        "can you help me",
        "can u help me",
    )

    if any(phrase in normalized for phrase in help_phrases):
        return (
            "I can help you manage and understand your business finances. "
            "Here are some things you can ask me:\n\n"
            "1. Receivables: How much money do my customers owe me?\n"
            "2. Payables: How much do I owe my suppliers?\n"
            "3. Overdue invoices: Which customer invoices are overdue?\n"
            "4. Monthly performance: How has my business performed recently?\n"
            "5. Cash-flow forecast: What is my expected cash flow?"
        )

    # Politely redirect questions outside the assistant's scope.
    return (
        "I'm designed to help with business finance questions. "
        "I can assist with receivables, payables, overdue invoices, "
        "monthly financial performance, and cash-flow forecasts. "
        "Please ask me something related to your business finances."
    )


def answer_finance_question(
    question: str,
    business_id: str,
    invoices: list[dict] | None = None,
    payments: list[dict] | None = None,
    expenses: list[dict] | None = None,
    monthly_history: list[dict] | None = None,
    opening_cash: float | None = None,
    today: date | None = None,
    forecast_months: int = 3,
    forecast_window: int = 12,
) -> AssistantResponse:
    """Answer a business finance question using approved Python tools.

    All data must be fetched and scoped by the backend before calling
    this function. This function does not connect to the database.

    Args:
        question: The user's finance-related question.
        business_id: Authenticated business ID.
        invoices: Business-scoped invoice records.
        payments: Business-scoped payment records.
        expenses: Business-scoped expense records.
        monthly_history: Business-scoped monthly cash history.
        opening_cash: Cash balance at the end of the last historical month.
        today: Optional date override, useful for testing overdue invoices.
        forecast_months: Number of future months to forecast.
        forecast_window: Number of recent historical months used for averages.

    Returns:
        An AssistantResponse containing the answer and actual tool data.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question cannot be empty.")

    if not isinstance(business_id, str) or not business_id.strip():
        raise ValueError("Business ID cannot be empty.")

    question = question.strip()
    business_id = business_id.strip()

    # Step 1: Create Groq client and select an approved tool.
    try:
        client = _get_client()
        tool_name = _select_tool(client, question)

    except APIError:
        logger.exception("Groq API failed during tool selection.")
        return _service_unavailable_response(question)

    # Step 2: Handle questions that do not require a financial tool.
    if tool_name is None:
        return AssistantResponse(
            question=question,
            answer=_fallback_answer(question),
            tool_used=None,
            data=None,
            insufficient_data=False,
        )

    # Step 3: Build arguments using data supplied by the backend.
    arguments = _build_tool_arguments(
        tool_name=tool_name,
        business_id=business_id,
        invoices=invoices,
        payments=payments,
        expenses=expenses,
        monthly_history=monthly_history,
        opening_cash=opening_cash,
        today=today,
        forecast_months=forecast_months,
        forecast_window=forecast_window,
    )

    # Step 4: Execute only the approved Python function.
    tool_function = TOOLS[tool_name]
    tool_result = tool_function(**arguments)

    if not isinstance(tool_result, dict):
        raise TypeError("An approved assistant tool must return a dictionary.")

    # Convert Decimal/date values into JSON-safe values for the response.
    safe_result = json.loads(json.dumps(tool_result, default=str))

    # Step 5: Check whether the result indicates insufficient history.
    insufficient_data = (
        safe_result.get("insufficient_data", False) is True
    )

    if (
        tool_name == "get_monthly_performance"
        and safe_result.get("months_available", 0) == 0
    ):
        insufficient_data = True

    # A forecast with no historical data is also insufficient.
    if (
        tool_name == "get_cash_forecast"
        and safe_result.get("method") == "insufficient_data"
    ):
        insufficient_data = True

    # Step 6: Ask Groq to explain the actual calculated result.
    try:
        answer = _make_answer(
            client=client,
            question=question,
            tool_name=tool_name,
            tool_result=safe_result,
        )

    except APIError:
        logger.exception("Groq API failed during answer generation.")

        # Python has already calculated the result.
        # Preserve it even when Groq cannot explain it.
        answer = (
            "Your financial data was calculated successfully, "
            "but the AI service is temporarily unavailable to explain it. "
            "Please try again shortly. The calculated data is included below."
        )

    return AssistantResponse(
        question=question,
        answer=answer,
        tool_used=tool_name,
        data=safe_result,
        insufficient_data=insufficient_data,
    )
