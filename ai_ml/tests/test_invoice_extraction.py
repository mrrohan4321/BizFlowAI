
from decimal import Decimal
from types import SimpleNamespace

import pytest
from ai_ml import invoice_extraction
from ai_ml.schemas import InvoiceFields, Severity


def valid_invoice():
    return InvoiceFields(
        invoice_number="INV-001",
        invoice_type="sales",
        party_name="ABC Traders",
        invoice_date="2026-11-15",
        due_date="2026-11-30",
        subtotal=Decimal("6000"),
        tax_amount=Decimal("1080"),
        cgst=Decimal("540"),
        sgst=Decimal("540"),
        total_amount=Decimal("7080"),
        gstin="19ABCDE1234F1Z5",
    )


def test_successful_extraction_and_validation(monkeypatch, tmp_path):
    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_text",
        lambda path: "Sample invoice OCR text",
    )

    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_fields",
        lambda text: valid_invoice(),
    )

    result = invoice_extraction.extract_invoice(
        tmp_path / "invoice.png"
    )

    assert result.fields.invoice_number == "INV-001"
    assert result.fields.total_amount == Decimal("7080")
    assert result.issues == []
    assert result.needs_review is True


def test_extraction_returns_validation_warnings(monkeypatch, tmp_path):
    invoice = valid_invoice()
    invoice.total_amount = Decimal("9000")

    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_text",
        lambda path: "Incorrect invoice OCR text",
    )

    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_fields",
        lambda text: invoice,
    )

    result = invoice_extraction.extract_invoice(
        tmp_path / "invoice.png"
    )

    assert result.needs_review is True
    assert any(
        issue.field == "total_amount"
        and issue.severity == Severity.WARNING
        for issue in result.issues
    )


def test_extraction_failure_returns_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_text",
        lambda path: "Sample invoice OCR text",
    )

    def fail_extraction(text):
        raise ValueError("Simulated extraction failure")

    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_fields",
        fail_extraction,
    )

    result = invoice_extraction.extract_invoice(
        tmp_path / "invoice.png"
    )

    assert result.needs_review is True
    assert len(result.issues) == 1
    assert result.issues[0].severity == Severity.ERROR
    assert result.fields.invoice_number is None


def test_api_failure_returns_structured_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_text",
        lambda path: "Sample invoice OCR text",
    )

    def fail_extraction(text):
        raise RuntimeError("Simulated service failure")

    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_fields",
        fail_extraction,
    )

    result = invoice_extraction.extract_invoice(
        tmp_path / "invoice.png"
    )

    assert result.needs_review is True
    assert result.fields.invoice_number is None
    assert len(result.issues) == 1
    assert result.issues[0].severity == Severity.ERROR
    assert "Simulated service failure" in result.issues[0].message


def test_empty_ocr_text_returns_structured_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_text",
        lambda path: "",
    )

    def fail_extraction(text):
        raise ValueError("OCR text is empty")

    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_fields",
        fail_extraction,
    )

    result = invoice_extraction.extract_invoice(
        tmp_path / "invoice.png"
    )

    assert result.needs_review is True
    assert result.fields.invoice_number is None
    assert result.issues[0].severity == Severity.ERROR

def mock_groq_response(monkeypatch, response):
    """Replace Groq with a fake client returning a controlled response."""

    class FakeCompletions:
        def create(self, **kwargs):
            return response

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=FakeCompletions()
        )
    )

    monkeypatch.setattr(
        invoice_extraction,
        "Groq",
        lambda **kwargs: fake_client,
    )

    monkeypatch.setattr(
        invoice_extraction.config,
        "require_groq_api_key",
        lambda: "fake-test-key",
    )


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(choices=[]),
        SimpleNamespace(choices=None),
        SimpleNamespace(),
    ],
)
def test_rejects_missing_or_empty_groq_choices(
    monkeypatch,
    response,
):
    mock_groq_response(monkeypatch, response)

    with pytest.raises(ValueError):
        invoice_extraction.extract_invoice_fields(
            "Sample invoice text"
        )


@pytest.mark.parametrize(
    "content",
    [
        None,
        123,
        "",
        "   ",
        "{invalid json",
        "[]",
        "null",
    ],
)
def test_rejects_invalid_groq_response_content(
    monkeypatch,
    content,
):
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )

    mock_groq_response(monkeypatch, response)

    with pytest.raises(ValueError):
        invoice_extraction.extract_invoice_fields(
            "Sample invoice text"
        )


def test_rejects_missing_groq_message(monkeypatch):
    response = SimpleNamespace(
        choices=[SimpleNamespace()]
    )

    mock_groq_response(monkeypatch, response)

    with pytest.raises(ValueError):
        invoice_extraction.extract_invoice_fields(
            "Sample invoice text"
        )


def test_rejects_invalid_invoice_schema_from_groq(monkeypatch):
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"invoice_date": "not-a-valid-date"}'
                )
            )
        ]
    )

    mock_groq_response(monkeypatch, response)

    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        invoice_extraction.extract_invoice_fields(
            "Sample invoice text"
        )


def test_ocr_errors_are_not_hidden(monkeypatch, tmp_path):
    def fail_ocr(path):
        raise RuntimeError("Simulated OCR failure")

    monkeypatch.setattr(
        invoice_extraction,
        "extract_invoice_text",
        fail_ocr,
    )

    with pytest.raises(RuntimeError, match="Simulated OCR failure"):
        invoice_extraction.extract_invoice(
            tmp_path / "invoice.png"
        )

