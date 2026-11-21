
"""Tests for the Groq-powered finance assistant.

Groq is mocked, so these tests never make real API requests.
"""

import json
from datetime import date
from types import SimpleNamespace

import pytest

from ai_ml import assistant


class FakeGroqClient:
    """Simulate Groq responses without making API calls."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self.create)
        )

    def create(self, **kwargs):
        self.calls.append(kwargs)

        if not self.responses:
            raise AssertionError("Unexpected Groq API call.")

        content = self.responses.pop(0)

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content)
                )
            ]
        )


def mock_groq(monkeypatch, tool_name):
    """Replace the real Groq client with two predictable responses."""

    fake_client = FakeGroqClient(
        [
            json.dumps({"tool_name": tool_name}),
            "Here is your financial summary.",
        ]
    )

    monkeypatch.setattr(
        assistant,
        "_get_client",
        lambda: fake_client,
    )

    return fake_client


@pytest.mark.parametrize(
    "tool_name,question,extra_data",
    [
        (
            "get_receivables_summary",
            "How much money do customers owe us?",
            {
                "invoices": [],
                "payments": [],
            },
        ),
        (
            "get_payables_summary",
            "How much do we owe suppliers?",
            {
                "invoices": [],
                "payments": [],
            },
        ),
        (
            "get_overdue_invoices",
            "Show me overdue invoices.",
            {
                "invoices": [],
                "payments": [],
                "today": date(2026, 11, 18),
            },
        ),
        (
            "get_monthly_performance",
            "Show our monthly financial performance.",
            {
                "monthly_history": [
                    {
                        "month": "2026-08",
                        "income": 10000,
                        "outflows": 5000,
                    }
                ],
            },
        ),
        (
            "get_cash_forecast",
            "Forecast our future cash flow.",
            {
                "monthly_history": [
                    {
                        "month": "2026-08",
                        "income": 10000,
                        "outflows": 5000,
                    }
                ],
                "opening_cash": 20000,
            },
        ),
    ],
)
def test_approved_tool_execution(
    monkeypatch,
    tool_name,
    question,
    extra_data,
):
    """Every approved tool can be selected and executed."""

    fake_client = mock_groq(monkeypatch, tool_name)

    result = assistant.answer_finance_question(
        question=question,
        business_id="business-123",
        **extra_data,
    )

    assert result.question == question
    assert result.tool_used == tool_name
    assert result.answer == "Here is your financial summary."
    assert result.data is not None
    assert result.data["business_id"] == "business-123"

    # One call selects the tool; the second explains its result.
    assert len(fake_client.calls) == 2


def test_unsupported_question(monkeypatch):
    """Unsupported questions should not execute any financial tool."""

    fake_client = FakeGroqClient(
        [json.dumps({"tool_name": None})]
    )

    monkeypatch.setattr(
        assistant,
        "_get_client",
        lambda: fake_client,
    )

    result = assistant.answer_finance_question(
        question="What is the weather today?",
        business_id="business-123",
    )

    assert result.tool_used is None
    assert result.data is None
    assert result.insufficient_data is False
    assert "receivables" in result.answer.lower()
    assert len(fake_client.calls) == 1


@pytest.mark.parametrize(
    "question,expected_text",
    [
        ("hi", "hello"),
        ("hello", "hello"),
        ("good morning", "hello"),
    ],
)
def test_greetings_receive_a_friendly_response(
    monkeypatch,
    question,
    expected_text,
):
    """Greetings should receive a friendly response, not a missing-data warning."""

    fake_client = FakeGroqClient(
        [json.dumps({"tool_name": None})]
    )

    monkeypatch.setattr(
        assistant,
        "_get_client",
        lambda: fake_client,
    )

    result = assistant.answer_finance_question(
        question=question,
        business_id="business-123",
    )

    assert result.tool_used is None
    assert result.data is None
    assert result.insufficient_data is False
    assert expected_text in result.answer.lower()
    assert "receivables" in result.answer.lower()
    assert len(fake_client.calls) == 1


@pytest.mark.parametrize(
    "question",
    [
        "How can u help me?",
        "How can you help me?",
        "What can you do?",
        "What can I ask you?",
    ],
)
def test_capability_questions_explain_assistant_features(
    monkeypatch,
    question,
):
    """Capability questions should explain the assistant's supported features."""

    fake_client = FakeGroqClient(
        [json.dumps({"tool_name": None})]
    )

    monkeypatch.setattr(
        assistant,
        "_get_client",
        lambda: fake_client,
    )

    result = assistant.answer_finance_question(
        question=question,
        business_id="business-123",
    )

    assert result.tool_used is None
    assert result.data is None
    assert result.insufficient_data is False

    answer = result.answer.lower()

    assert "receivables" in answer
    assert "payables" in answer
    assert "overdue invoices" in answer
    assert "cash-flow forecast" in answer

    assert len(fake_client.calls) == 1


def test_invalid_tool_selection(monkeypatch):
    """The assistant must reject tools outside its approved registry."""

    fake_client = FakeGroqClient(
        [json.dumps({"tool_name": "delete_database"})]
    )

    monkeypatch.setattr(
        assistant,
        "_get_client",
        lambda: fake_client,
    )

    with pytest.raises(ValueError, match="not approved"):
        assistant.answer_finance_question(
            question="Show financial information.",
            business_id="business-123",
        )


def test_missing_invoice_data(monkeypatch):
    """Invoice-related tools require invoice and payment data."""

    mock_groq(monkeypatch, "get_receivables_summary")

    with pytest.raises(ValueError, match="must be supplied"):
        assistant.answer_finance_question(
            question="How much do customers owe us?",
            business_id="business-123",
        )


def test_missing_monthly_history(monkeypatch):
    """Monthly tools must not run without historical records being supplied."""

    mock_groq(monkeypatch, "get_monthly_performance")

    with pytest.raises(ValueError, match="Monthly financial history"):
        assistant.answer_finance_question(
            question="Show monthly performance.",
            business_id="business-123",
        )


def test_missing_opening_cash(monkeypatch):
    """Cash forecasting requires an opening cash balance."""

    mock_groq(monkeypatch, "get_cash_forecast")

    with pytest.raises(ValueError, match="Opening cash"):
        assistant.answer_finance_question(
            question="Forecast future cash flow.",
            business_id="business-123",
            monthly_history=[
                {
                    "month": "2026-08",
                    "income": 10000,
                    "outflows": 5000,
                }
            ],
        )


def test_empty_question():
    """An empty question must be rejected."""

    with pytest.raises(ValueError, match="Question cannot be empty"):
        assistant.answer_finance_question(
            question="   ",
            business_id="business-123",
        )


def test_empty_business_id():
    """A missing business ID must be rejected."""

    with pytest.raises(ValueError, match="Business ID cannot be empty"):
        assistant.answer_finance_question(
            question="Show receivables.",
            business_id="   ",
        )


class SimulatedGroqAPIError(Exception):
    """Fake Groq API error for testing."""


def test_groq_failure_during_tool_selection(monkeypatch):
    """A Groq failure during tool selection returns a safe response."""

    monkeypatch.setattr(
        assistant,
        "APIError",
        SimulatedGroqAPIError,
    )

    monkeypatch.setattr(
        assistant,
        "_get_client",
        lambda: object(),
    )

    def fail_tool_selection(client, question):
        raise SimulatedGroqAPIError("Simulated API failure")

    monkeypatch.setattr(
        assistant,
        "_select_tool",
        fail_tool_selection,
    )

    result = assistant.answer_finance_question(
        question="How much do customers owe us?",
        business_id="business-123",
    )

    assert result.tool_used is None
    assert result.data is None
    assert result.insufficient_data is True
    assert "temporarily unavailable" in result.answer.lower()


def test_groq_failure_during_answer_generation(monkeypatch):
    """Calculated financial data is preserved if Groq cannot explain it."""

    monkeypatch.setattr(
        assistant,
        "APIError",
        SimulatedGroqAPIError,
    )

    mock_groq(monkeypatch, "get_receivables_summary")

    def fail_answer_generation(**kwargs):
        raise SimulatedGroqAPIError("Simulated API failure")

    monkeypatch.setattr(
        assistant,
        "_make_answer",
        fail_answer_generation,
    )

    result = assistant.answer_finance_question(
        question="How much do customers owe us?",
        business_id="business-123",
        invoices=[],
        payments=[],
    )

    assert result.tool_used == "get_receivables_summary"
    assert result.data is not None
    assert result.data["business_id"] == "business-123"
    assert "calculated successfully" in result.answer.lower()


@pytest.mark.parametrize(
    "question,business_id",
    [
        (None, "business-123"),
        (123, "business-123"),
        ("Show receivables.", None),
        ("Show receivables.", 123),
    ],
)
def test_rejects_invalid_question_and_business_id(
    question,
    business_id,
):
    with pytest.raises(ValueError):
        assistant.answer_finance_question(
            question=question,
            business_id=business_id,
        )


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        "{}",
        '{"tool_name": "delete_database"}',
        '{"tool_name": null, "extra": "unexpected"}',
    ],
)
def test_rejects_invalid_tool_selection_response(
    monkeypatch,
    content,
):
    fake_client = FakeGroqClient([content])

    with pytest.raises(ValueError):
        assistant._select_tool(fake_client, "Show receivables.")


def test_forecast_parameters_are_forwarded(monkeypatch):
    fake_client = mock_groq(monkeypatch, "get_cash_forecast")

    result = assistant.answer_finance_question(
        question="Forecast future cash flow.",
        business_id="business-123",
        monthly_history=[
            {
                "month": "2026-08",
                "income": 10000,
                "outflows": 5000,
            },
            {
                "month": "2026-09",
                "income": 12000,
                "outflows": 6000,
            },
        ],
        opening_cash=20000,
        forecast_months=2,
        forecast_window=2,
    )

    assert result.tool_used == "get_cash_forecast"
    assert len(result.data["periods"]) == 2
    assert len(fake_client.calls) == 2


def test_rejects_empty_groq_answer(monkeypatch):
    fake_client = FakeGroqClient(
        [
            json.dumps({"tool_name": "get_receivables_summary"}),
            "   ",
        ]
    )

    monkeypatch.setattr(
        assistant,
        "_get_client",
        lambda: fake_client,
    )

    with pytest.raises(ValueError, match="empty assistant answer"):
        assistant.answer_finance_question(
            question="How much do customers owe us?",
            business_id="business-123",
            invoices=[],
            payments=[],
        )
