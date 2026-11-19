
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_ml.schemas import InvoiceFields
from ai_ml.validation import validate_invoice


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "messy_invoice_scenarios.json"
)


with FIXTURE_PATH.open("r", encoding="utf-8") as file:
    DATASET = json.load(file)


@pytest.mark.parametrize(
    "case",
    DATASET["cases"],
    ids=lambda case: case["id"],
)
def test_messy_invoice_scenario(case):
    invoice_data = case["invoice"]

    if case["expected_schema_error"]:
        with pytest.raises(ValidationError):
            InvoiceFields(**invoice_data)

        return

    invoice = InvoiceFields(**invoice_data)
    issues = validate_invoice(invoice)

    actual_issues = {
        (issue.field, issue.severity.value)
        for issue in issues
    }

    expected_issues = {
        (issue["field"], issue["severity"])
        for issue in case["expected_issues"]
    }

    assert actual_issues == expected_issues, (
        f"Unexpected validation results for {case['id']}"
    )


def test_dataset_contains_unique_case_ids():
    case_ids = [
        case["id"]
        for case in DATASET["cases"]
    ]

    assert len(case_ids) == len(set(case_ids))


def test_dataset_has_valid_and_messy_invoices():
    cases = DATASET["cases"]

    assert any(
        not case["expected_schema_error"]
        and not case["expected_issues"]
        for case in cases
    )

    assert any(
        case["expected_issues"]
        for case in cases
    )

    assert any(
        case["expected_schema_error"]
        for case in cases
    )
