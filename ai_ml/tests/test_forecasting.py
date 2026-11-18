
import pytest
from datetime import date

from ai_ml.forecasting import baseline_forecast, get_forecast


def test_three_month_baseline():
    result = baseline_forecast([10000, 20000, 30000])
    assert result == 20000


def test_baseline_uses_only_recent_months():
    result = baseline_forecast(
        [10000, 20000, 30000, 40000],
        window=3,
    )
    assert result == 30000


def test_empty_history_returns_insufficient_data():
    result = get_forecast([])

    assert result["periods"] == []
    assert result["values"] == []
    assert result["method"] == "insufficient_data"


def test_forecast_calculates_closing_cash():
    history = [
        {"month": "2026-08", "income": 30000, "outflows": 20000},
        {"month": "2026-09", "income": 40000, "outflows": 25000},
        {"month": "2026-10", "income": 50000, "outflows": 30000},
    ]

    result = get_forecast(
        history,
        opening_cash=100000,
        forecast_months=1,
    )

    assert result["periods"] == ["2026-11"]
    assert result["values"][0]["predicted_income"] == 40000
    assert result["values"][0]["predicted_outflows"] == 25000
    assert result["values"][0]["predicted_closing_cash"] == 115000


def test_multiple_future_months():
    history = [
        {"month": "2026-08", "income": 30000, "outflows": 20000},
        {"month": "2026-09", "income": 30000, "outflows": 20000},
        {"month": "2026-10", "income": 30000, "outflows": 20000},
    ]

    result = get_forecast(
        history,
        opening_cash=50000,
        forecast_months=3,
    )

    assert result["periods"] == [
        "2026-11",
        "2026-12",
        "2027-01",
    ]

    assert result["values"][0]["predicted_closing_cash"] == 60000
    assert result["values"][1]["predicted_closing_cash"] == 70000
    assert result["values"][2]["predicted_closing_cash"] == 80000


def test_december_to_january_transition():
    history = [
        {"month": "2026-12", "income": 10000, "outflows": 5000},
    ]

    result = get_forecast(
        history,
        opening_cash=20000,
        forecast_months=1,
        window=1,
    )

    assert result["periods"] == ["2027-01"]
    assert result["closing_cash"] == 25000


def test_invalid_window_raises_error():
    with pytest.raises(ValueError):
        baseline_forecast([10000, 20000], window=0)


def test_invalid_forecast_months_raises_error():
    with pytest.raises(ValueError):
        get_forecast([], forecast_months=0)


# --------------------------------------------------
# Forecast input validation tests
# --------------------------------------------------

@pytest.mark.parametrize(
    "value",
    [True, False, float("nan"), float("inf"), -float("inf")],
)
def test_money_rejects_invalid_values(value):
    from ai_ml.forecasting import money

    with pytest.raises(ValueError):
        money(value)


def test_baseline_rejects_negative_values():
    with pytest.raises(ValueError):
        baseline_forecast([1000, -500])


def test_baseline_rejects_boolean_values():
    with pytest.raises(ValueError):
        baseline_forecast([1000, True])


@pytest.mark.parametrize("window", [0, -1, 1.5, True])
def test_baseline_rejects_invalid_window(window):
    with pytest.raises(ValueError):
        baseline_forecast([1000, 2000], window=window)


def test_forecast_rejects_negative_income():
    history = [{
        "month": "2026-10",
        "income": -1000,
        "outflows": 500,
    }]

    with pytest.raises(ValueError, match="Historical income"):
        get_forecast(history)


def test_forecast_rejects_negative_outflows():
    history = [{
        "month": "2026-10",
        "income": 1000,
        "outflows": -500,
    }]

    with pytest.raises(ValueError, match="Historical outflows"):
        get_forecast(history)


def test_forecast_allows_negative_opening_cash():
    history = [{
        "month": "2026-10",
        "income": 1000,
        "outflows": 500,
    }]

    result = get_forecast(
        history,
        opening_cash=-5000,
        forecast_months=1,
        window=1,
    )

    assert result["opening_cash"] == -5000
    assert result["closing_cash"] == -4500


def test_forecast_sorts_history_chronologically():
    history = [
        {"month": "2026-10", "income": 30000, "outflows": 15000},
        {"month": "2026-08", "income": 10000, "outflows": 5000},
        {"month": "2026-09", "income": 20000, "outflows": 10000},
    ]

    result = get_forecast(
        history,
        forecast_months=1,
        window=3,
    )

    assert result["periods"] == ["2026-11"]
    assert result["values"][0]["predicted_income"] == 20000
    assert result["values"][0]["predicted_outflows"] == 10000


def test_forecast_rejects_duplicate_months():
    history = [
        {"month": "2026-10", "income": 10000, "outflows": 5000},
        {"month": "2026-10", "income": 20000, "outflows": 10000},
    ]

    with pytest.raises(ValueError, match="Duplicate"):
        get_forecast(history)


def test_forecast_rejects_invalid_month():
    history = [{
        "month": "2026-13",
        "income": 1000,
        "outflows": 500,
    }]

    with pytest.raises(ValueError, match="YYYY-MM"):
        get_forecast(history)


def test_forecast_rejects_missing_history_field():
    history = [{
        "month": "2026-10",
        "income": 1000,
    }]

    with pytest.raises(ValueError, match="outflows"):
        get_forecast(history)


def test_forecast_reports_actual_history_used():
    history = [
        {"month": "2026-09", "income": 10000, "outflows": 5000},
        {"month": "2026-10", "income": 20000, "outflows": 10000},
    ]

    result = get_forecast(
        history,
        forecast_months=1,
        window=3,
    )

    assert result["months_of_history_used"] == 2
    assert result["method"] == "2-month moving average"


def test_forecast_accepts_date_objects():
    history = [{
        "month": date(2026, 10, 15),
        "income": 10000,
        "outflows": 5000,
    }]

    result = get_forecast(
        history,
        forecast_months=1,
        window=1,
    )

    assert result["periods"] == ["2026-11"]


def test_forecast_rejects_invalid_forecast_month_count():
    with pytest.raises(ValueError):
        get_forecast([], forecast_months=1.5)
