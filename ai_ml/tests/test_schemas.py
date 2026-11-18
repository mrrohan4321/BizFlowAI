
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ai_ml.schemas import InvoiceFields


def test_rupee_symbol_is_parsed():
    invoice = InvoiceFields(total_amount="₹30,000.50")

    assert invoice.total_amount == Decimal("30000.50")


def test_indian_comma_grouping_is_parsed():
    invoice = InvoiceFields(total_amount="₹1,23,456.78")

    assert invoice.total_amount == Decimal("123456.78")


def test_international_comma_grouping_is_parsed():
    invoice = InvoiceFields(total_amount="123,456.78")

    assert invoice.total_amount == Decimal("123456.78")


def test_unsupported_currency_prefix_is_rejected():
    with pytest.raises(ValidationError):
        InvoiceFields(total_amount="USD 123,456.78")


def test_rupees_prefix_is_parsed():
    invoice = InvoiceFields(total_amount="Rs. 12,500")

    assert invoice.total_amount == Decimal("12500")


def test_inr_prefix_is_parsed():
    invoice = InvoiceFields(total_amount="INR 500")

    assert invoice.total_amount == Decimal("500")


def test_empty_amount_becomes_none():
    invoice = InvoiceFields(total_amount="   ")

    assert invoice.total_amount is None


def test_none_amount_remains_none():
    invoice = InvoiceFields(total_amount=None)

    assert invoice.total_amount is None


@pytest.mark.parametrize(
    "value",
    [
        "not an amount",
        "12,34,56",
        "1,2,3",
        "₹",
        "Rs. invalid",
    ],
)
def test_invalid_amount_strings_are_rejected(value):
    with pytest.raises(ValidationError):
        InvoiceFields(total_amount=value)


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_non_finite_amounts_are_rejected(value):
    with pytest.raises(ValidationError):
        InvoiceFields(total_amount=value)


def test_boolean_is_not_an_amount():
    with pytest.raises(ValidationError):
        InvoiceFields(total_amount=True)


def test_gstin_is_normalized_to_uppercase():
    invoice = InvoiceFields(gstin="19abcde1234f1z5")

    assert invoice.gstin == "19ABCDE1234F1Z5"


def test_empty_text_fields_become_none():
    invoice = InvoiceFields(
        invoice_number="  ",
        party_name=" ",
        gstin=" ",
    )

    assert invoice.invoice_number is None
    assert invoice.party_name is None
    assert invoice.gstin is None


def test_invoice_type_is_normalized():
    invoice = InvoiceFields(invoice_type=" SALES ")

    assert invoice.invoice_type == "sales"


def test_invalid_invoice_type_is_rejected():
    with pytest.raises(ValidationError):
        InvoiceFields(invoice_type="refund")


def test_extra_fields_are_ignored():
    invoice = InvoiceFields(
        total_amount="1000",
        unknown_field="unexpected",
    )

    assert invoice.total_amount == Decimal("1000")
    assert not hasattr(invoice, "unknown_field")
