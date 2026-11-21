
import json
from types import SimpleNamespace

import groq
import httpx
import pytest

from tests.conftest import add_expense, add_payment, known_answer, set_opening


class FakeGroq:
    """Stands in for the Groq client: 1st call = tool selection (JSON mode), 2nd call = explanation."""

    def __init__(self, tool, explanation="Here is your answer.", fail=False):
        self.tool, self.explanation, self.fail, self.calls = tool, explanation, fail, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com"))
        text = json.dumps({"tool_name": self.tool}) if kw.get("response_format") else self.explanation
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


@pytest.fixture
def fake(monkeypatch):
    def install(tool, **kw):
        client = FakeGroq(tool, **kw)
        monkeypatch.setattr("ai_ml.assistant._get_client", lambda: client)
        return client
    return install


def ask(client, headers, q="How much do my customers owe me?"):
    return client.post("/api/assistant/chat", json={"question": q}, headers=headers)


def test_requires_authentication(client):
    assert client.post("/api/assistant/chat", json={"question": "hi"}).status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"question": ""},
        {"question": "   "},
        {"question": "x" * 501},
        {"question": "ok", "business_id": "abc"},
    ],
)
def test_invalid_questions_rejected(client, world, body):
    assert client.post(
        "/api/assistant/chat",
        json=body,
        headers=world.h_a,
    ).status_code == 422


def test_receivables_answer_uses_python_numbers(client, world, fake):
    known_answer(world, world.biz_a)
    f = fake("get_receivables_summary", explanation="Customers owe you 45000.")

    r = ask(client, world.h_a)

    assert r.status_code == 200
    j = r.json()
    assert j["tool_used"] == "get_receivables_summary"
    assert j["answer"] == "Customers owe you 45000."
    assert j["data_used"]["receivables"] == 45000.0
    assert j["data"] == j["data_used"]
    assert j["insufficient_data"] is False
    assert j["follow_up"]
    assert len(f.calls) == 2


def test_payables_and_overdue_tools(client, world, fake):
    known_answer(world, world.biz_a)
    world.invoice(world.biz_a, "LATE", "sales", "100.00", due="2020-01-01")

    fake("get_payables_summary")
    assert ask(
        client,
        world.h_a,
        "What do I owe suppliers?",
    ).json()["data_used"]["payables"] == 20000.0

    fake("get_overdue_invoices")
    j = ask(
        client,
        world.h_a,
        "Which invoices are overdue?",
    ).json()

    assert j["data_used"]["count"] >= 1
    assert any(
        i["invoice_number"] == "LATE"
        for i in j["data_used"]["invoices"]
    )


def test_monthly_performance_and_missing_history(client, world, fake):
    fake("get_monthly_performance")

    j = ask(
        client,
        world.h_a,
        "How did I do this month?",
    ).json()

    assert j["insufficient_data"] is True
    assert j["data_used"]["months_available"] == 0

    sale = world.invoice(world.biz_a, "S", "sales", "5000.00")
    add_payment(world, world.biz_a, sale, "5000.00", "2026-10-02")
    add_expense(world, world.biz_a, "2000.00", "2026-10-03", paid_on="2026-10-03")

    j = ask(
        client,
        world.h_a,
        "How did I do?",
    ).json()

    assert j["insufficient_data"] is False
    assert j["data_used"]["net_cash_movement"] == 3000.0


def test_cash_forecast_through_assistant(client, world, fake):
    sale = world.invoice(world.biz_a, "S", "sales", "90000.00")
    add_payment(world, world.biz_a, sale, "30000.00", "2026-10-02")
    set_opening(world, world.biz_a, "1000.00", "2026-10-31")

    fake("get_cash_forecast")

    j = ask(
        client,
        world.h_a,
        "What is my expected cash flow?",
    ).json()

    assert j["tool_used"] == "get_cash_forecast"
    assert j["data_used"]["periods"][0] == "2026-11"


def test_cash_forecast_without_opening_cash_is_explained_not_guessed(
    client,
    world,
    fake,
):
    fake("get_cash_forecast")

    r = ask(
        client,
        world.h_a,
        "What is my expected cash flow?",
    )

    assert r.status_code == 200
    j = r.json()

    assert j["insufficient_data"] is True
    assert "opening cash" in j["answer"].lower()
    assert j["data_used"] is None


def test_unsupported_question_is_declined(client, world, fake):
    fake(None)

    j = ask(
        client,
        world.h_a,
        "Should I buy bitcoin?",
    ).json()

    assert j["tool_used"] is None
    assert j["insufficient_data"] is False
    assert j["data_used"] is None
    assert "receivables" in j["answer"].lower()


@pytest.mark.parametrize(
    "question,expected_text",
    [
        ("hi", "hello"),
        ("hello", "hello"),
        ("good morning", "hello"),
    ],
)
def test_greetings_receive_friendly_responses(
    client,
    world,
    fake,
    question,
    expected_text,
):
    fake(None)

    j = ask(
        client,
        world.h_a,
        question,
    ).json()

    assert j["tool_used"] is None
    assert j["data_used"] is None
    assert j["insufficient_data"] is False
    assert expected_text in j["answer"].lower()
    assert "receivables" in j["answer"].lower()


@pytest.mark.parametrize(
    "question",
    [
        "How can u help me?",
        "How can you help me?",
        "What can you do?",
        "What can I ask you?",
    ],
)
def test_capability_questions_explain_supported_features(
    client,
    world,
    fake,
    question,
):
    fake(None)

    j = ask(
        client,
        world.h_a,
        question,
    ).json()

    assert j["tool_used"] is None
    assert j["data_used"] is None
    assert j["insufficient_data"] is False

    answer = j["answer"].lower()

    assert "receivables" in answer
    assert "payables" in answer
    assert "overdue invoices" in answer
    assert "cash-flow forecast" in answer


def test_groq_outage_does_not_leak_details_or_invent_numbers(client, world, fake):
    known_answer(world, world.biz_a)
    fake("get_receivables_summary", fail=True)

    r = ask(client, world.h_a)

    assert r.status_code == 200
    j = r.json()

    assert j["insufficient_data"] is True
    assert j["tool_used"] is None
    assert j["data_used"] is None
    assert "temporarily unavailable" in j["answer"]
    assert "groq" not in r.text.lower()


def test_missing_api_key_returns_503(client, world, monkeypatch):
    monkeypatch.setattr("ai_ml.config.GROQ_API_KEY", None)

    r = ask(client, world.h_a)

    assert r.status_code == 503
    assert r.json()["error"]["code"] == "ai_not_configured"


def test_bad_ai_response_is_a_clean_502(client, world, fake):
    fake("not_an_approved_tool")

    r = ask(client, world.h_a)

    assert r.status_code == 502
    assert r.json()["error"]["code"] == "assistant_failed"
    assert "approved" not in r.text


def test_other_business_data_is_never_sent_to_groq(client, world, fake):
    known_answer(world, world.biz_a)
    world.invoice(world.biz_b, "SECRET-B", "sales", "123456.00")

    f = fake("get_receivables_summary")
    j = ask(client, world.h_a).json()

    assert j["data_used"]["receivables"] == 45000.0

    sent = json.dumps(f.calls, default=str)

    assert "SECRET-B" not in sent
    assert "123456" not in sent
    assert world.biz_b not in sent

    # Business B only sees its own numbers.
    fb = fake("get_receivables_summary")

    assert ask(
        client,
        world.h_b,
    ).json()["data_used"]["receivables"] == 123456.0

    assert "45000" not in json.dumps(fb.calls, default=str)
