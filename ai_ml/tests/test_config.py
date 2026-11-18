
from decimal import Decimal

import pytest

from ai_ml import config


def test_project_root_is_correct():
    assert config.PROJECT_ROOT == config.AI_ML_DIR.parent


def test_sample_data_directory_points_to_project_root():
    assert config.SAMPLE_DATA_DIR == config.PROJECT_ROOT / "sample_data"


def test_sample_invoice_directory_exists():
    assert (config.SAMPLE_DATA_DIR / "invoices").is_dir()


def test_supported_extensions_are_correct():
    assert config.SUPPORTED_EXTENSIONS == {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
    }


def test_default_timeout_is_positive():
    assert config.GROQ_TIMEOUT_SECONDS > 0


def test_default_ocr_threshold_is_positive():
    assert config.MIN_TEXT_CHARS_PER_PAGE >= 1


def test_default_amount_tolerance_is_decimal():
    assert isinstance(config.AMOUNT_TOLERANCE, Decimal)
    assert config.AMOUNT_TOLERANCE >= 0


@pytest.mark.parametrize(
    "value",
    ["abc", "NaN", "inf", "-1", "0"],
)
def test_invalid_timeout_is_rejected(value):
    with pytest.raises(ValueError):
        config._parse_positive_float(
            "GROQ_TIMEOUT_SECONDS",
            value,
            "30",
        )


@pytest.mark.parametrize(
    "value",
    ["abc", "1.5", "0", "-1"],
)
def test_invalid_ocr_threshold_is_rejected(value):
    with pytest.raises(ValueError):
        config._parse_positive_int(
            "MIN_TEXT_CHARS_PER_PAGE",
            value,
            "30",
        )


@pytest.mark.parametrize(
    "value",
    ["abc", "NaN", "Infinity", "-1"],
)
def test_invalid_amount_tolerance_is_rejected(value):
    with pytest.raises(ValueError):
        config._parse_nonnegative_decimal(
            "AMOUNT_TOLERANCE",
            value,
            "1.00",
        )


def test_zero_amount_tolerance_is_allowed():
    result = config._parse_nonnegative_decimal(
        "AMOUNT_TOLERANCE",
        "0",
        "1.00",
    )

    assert result == Decimal("0")


def test_valid_custom_timeout_is_accepted():
    result = config._parse_positive_float(
        "GROQ_TIMEOUT_SECONDS",
        "45.5",
        "30",
    )

    assert result == 45.5


def test_valid_custom_ocr_threshold_is_accepted():
    result = config._parse_positive_int(
        "MIN_TEXT_CHARS_PER_PAGE",
        "50",
        "30",
    )

    assert result == 50


def test_valid_custom_amount_tolerance_is_accepted():
    result = config._parse_nonnegative_decimal(
        "AMOUNT_TOLERANCE",
        "0.50",
        "1.00",
    )

    assert result == Decimal("0.50")


def test_missing_groq_api_key_raises_clear_error(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", None)

    with pytest.raises(RuntimeError, match="GROQ_API_KEY is not set"):
        config.require_groq_api_key()


def test_existing_groq_api_key_is_returned(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")

    assert config.require_groq_api_key() == "test-key"
