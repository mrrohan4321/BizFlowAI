
import json
import logging
from pathlib import Path

from groq import Groq
from pydantic import ValidationError

from ai_ml import config
from ai_ml.ocr import extract_invoice_text
from ai_ml.schemas import (
    InvoiceFields,
    InvoiceExtractionResult,
    ValidationIssue,
    Severity,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are an expert invoice data extraction assistant.

Extract information from the supplied invoice text.

Return ONLY valid JSON with these fields:
- invoice_number
- invoice_type
- party_name
- invoice_date
- due_date
- subtotal
- tax_amount
- cgst
- sgst
- igst
- total_amount
- gstin

Rules:
1. Never invent missing information. Use null.
2. invoice_type must be "sales", "purchase", or null.
3. Dates must use YYYY-MM-DD format.
4. Amounts must be numeric values without currency symbols.
5. party_name means the customer or supplier named on the invoice.
6. Return only JSON, without Markdown code fences.
"""


def extract_invoice_fields(ocr_text: str) -> InvoiceFields:
    """Use Groq to extract structured fields from OCR text."""

    if not ocr_text.strip():
        raise ValueError("OCR text is empty. Cannot extract invoice data.")

    client = Groq(
        api_key=config.require_groq_api_key(),
        timeout=config.GROQ_TIMEOUT_SECONDS,
    )

    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract invoice information from this text:\n\n{ocr_text}",
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    response_text = response.choices[0].message.content

    if not response_text:
        raise ValueError("Groq returned an empty response.")

    extracted_data = json.loads(response_text)

    return InvoiceFields.model_validate(extracted_data)


def extract_invoice(file_path: str | Path) -> InvoiceExtractionResult:
    """Extract invoice data from a PDF or image."""

    file_path = Path(file_path)

    # Stage 1: OCR
    ocr_text = extract_invoice_text(file_path)

    # Stage 2: Groq extraction
    try:
        fields = extract_invoice_fields(ocr_text)

        return InvoiceExtractionResult(
            fields=fields,
            source_file=str(file_path),
            raw_text_preview=ocr_text[:1000],
            needs_review=True,
        )

    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        logger.exception("Invoice extraction failed.")

        return InvoiceExtractionResult(
            fields=InvoiceFields(),
            issues=[
                ValidationIssue(
                    severity=Severity.ERROR,
                    message=f"Invoice extraction failed: {exc}",
                )
            ],
            source_file=str(file_path),
            raw_text_preview=ocr_text[:1000],
            needs_review=True,
        )
