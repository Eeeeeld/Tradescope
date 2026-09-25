"""Analysis helpers built on pandas / numpy."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def periods_per_year(idx: pd.Index) -> float:
    gap = pd.Series(idx).diff().dt.days.median()
    return 365.0 / max(gap if pd.notna(gap) else 1, 1)


def log_returns(s: pd.Series) -> pd.Series:
    return np.log(s).diff().dropna()


def annual_vol(s: pd.Series) -> float:
    return float(log_returns(s).std() * np.sqrt(periods_per_year(s.index)) * 100)


def rolling_vol(s: pd.Series, window: int = 20) -> pd.Series:
    return log_returns(s).rolling(window).std() * np.sqrt(periods_per_year(s.index)) * 100


def summary(s: pd.Series) -> dict:
    s = s.dropna()
    return {
        "last": s.iloc[-1], "change_pct": (s.iloc[-1] / s.iloc[0] - 1) * 100,
        "high": s.max(), "low": s.min(), "mean": s.mean(), "vol": annual_vol(s),
        "high_date": s.idxmax(), "low_date": s.idxmin(),
    }


def change_over(s: pd.Series, days: int) -> float | None:
    """% change of the series over the last `days` calendar days."""
    s = s.dropna()
    if s.empty:
        return None
    past = s[s.index <= s.index[-1] - pd.Timedelta(days=days)]
    if past.empty:
        return None
    return (s.iloc[-1] / past.iloc[-1] - 1) * 100


def holt_forecast(s: pd.Series, horizon: int, alpha: float = 0.5, beta: float = 0.1) -> pd.DataFrame:
    """Holt's linear-trend exponential smoothing with a ~95% band. Illustrative only."""
    s = s.dropna()
    y = s.values
    level, trend = y[0], (y[1] - y[0]) if len(y) > 1 else 0.0
    fitted = []
    for v in y:
        fitted.append(level + trend)
        prev = level
        level = alpha * v + (1 - alpha) * (level + trend)
        trend = beta * (level - prev) + (1 - beta) * trend
    resid = y[1:] - np.array(fitted[:-1])
    sigma = resid.std() if len(resid) > 2 else 0.0
    step = pd.Series(s.index).diff().median() or pd.Timedelta(days=1)
    idx = pd.DatetimeIndex([s.index[-1] + step * (h + 1) for h in range(horizon)])
    h = np.arange(1, horizon + 1)
    yhat = level + trend * h
    band = 1.96 * sigma * np.sqrt(h)
    return pd.DataFrame({"forecast": yhat, "low": yhat - band, "high": yhat + band}, index=idx)


def strength_table(hist: pd.DataFrame, currencies: list[str], windows: dict[str, int]) -> pd.DataFrame:
    """% change in the TWD value of 1 unit of each currency. Positive = it strengthened vs TWD."""
    out = {}
    for c in currencies:
        value_in_twd = 1 / hist[c]
        out[c] = {label: change_over(value_in_twd, d) for label, d in windows.items()}
    return pd.DataFrame(out).T


def corr_matrix(hist: pd.DataFrame, currencies: list[str]) -> pd.DataFrame:
    rets = np.log(hist[currencies]).diff().dropna()
    return rets.corr()


def rolling_corr(a: pd.Series, b: pd.Series, window: int = 20) -> pd.Series:
    return log_returns(a).rolling(window).corr(log_returns(b))
