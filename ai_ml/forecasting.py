"""Forecast: recent-3-month baseline first; optional LinearRegression vs baseline
(chronological split, compare MAE)."""


def baseline_forecast(monthly_values: list[float], window: int = 3) -> float:
    recent = monthly_values[-window:]
    return sum(recent) / len(recent) if recent else 0.0


def get_forecast(monthly_history) -> dict:
    """Return {periods, values, method, assumptions}."""
    raise NotImplementedError
