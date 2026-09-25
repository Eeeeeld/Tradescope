"""Exchange-rate data.

Source: fawazahmed0 exchange-api (free, no key, daily, includes TWD and IDR).
  https://github.com/fawazahmed0/exchange-api
All rates are fetched with TWD as the base ("X per 1 TWD"); any other pair is
computed as a cross rate. If the network is unavailable the app falls back to a
clearly flagged synthetic sample so the UI still works.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st

CURRENCIES = ["TWD", "IDR", "USD", "EUR", "JPY", "CNY", "SGD", "MYR",
              "THB", "VND", "PHP", "KRW", "HKD", "AUD", "GBP", "INR"]

PRIMARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{tag}/v1/currencies/twd.min.json"
FALLBACK = "https://{tag}.currency-api.pages.dev/v1/currencies/twd.min.json"
EARLIEST = date(2024, 3, 2)   # first dated snapshot published by the API
TIMEOUT = 8

# Offline sample only (approximate levels, X per 1 TWD). Never shown as live data.
_SAMPLE_LEVELS = {"TWD": 1, "IDR": 510, "USD": 0.031, "EUR": 0.028, "JPY": 4.6, "CNY": 0.22,
                  "SGD": 0.040, "MYR": 0.135, "THB": 1.02, "VND": 810, "PHP": 1.78,
                  "KRW": 43.5, "HKD": 0.24, "AUD": 0.047, "GBP": 0.024, "INR": 2.7}


def _fetch_twd(tag: str) -> dict | None:
    """Fetch one snapshot ('latest' or 'YYYY-MM-DD'). Returns {'date', 'rates'} or None."""
    for url in (PRIMARY.format(tag=tag), FALLBACK.format(tag=tag)):
        try:
            r = requests.get(url, timeout=TIMEOUT)
            if r.ok:
                js = r.json()
                raw = js.get("twd", {})
                rates = {c: float(raw[c.lower()]) for c in CURRENCIES if c.lower() in raw}
                rates["TWD"] = 1.0
                return {"date": js.get("date", tag), "rates": rates}
        except (requests.RequestException, ValueError, KeyError):
            continue
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def latest() -> tuple[str, dict, bool]:
    """Returns (date, {CUR: units per 1 TWD}, is_sample)."""
    snap = _fetch_twd("latest")
    if snap:
        return snap["date"], snap["rates"], False
    return date.today().isoformat(), dict(_SAMPLE_LEVELS), True


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def history(days: int) -> tuple[pd.DataFrame, bool]:
    """DataFrame indexed by date, one column per currency (units per 1 TWD)."""
    end = date.today()
    start = max(end - timedelta(days=days), EARLIEST)
    step = max(1, (end - start).days // 90)          # keep to ~90 requests
    tags = []
    d = end
    while d >= start:
        tags.append(d.isoformat())
        d -= timedelta(days=step)

    with ThreadPoolExecutor(max_workers=16) as pool:
        snaps = [s for s in pool.map(_fetch_twd, tags) if s]

    if len(snaps) >= 3:
        rows = {pd.Timestamp(s["date"]): s["rates"] for s in snaps}
        df = pd.DataFrame.from_dict(rows, orient="index").sort_index()
        df = df[~df.index.duplicated()]
        return df[[c for c in CURRENCIES if c in df.columns]], False
    return sample_history(days), True


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def on_date(d: date) -> dict | None:
    snap = _fetch_twd(d.isoformat())
    return snap["rates"] if snap else None


def sample_history(days: int) -> pd.DataFrame:
    """Deterministic synthetic random walk (offline demo only)."""
    rng = np.random.default_rng(42)
    idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days + 1, freq="D")
    out = {}
    for c, lvl in _SAMPLE_LEVELS.items():
        if c == "TWD":
            out[c] = np.ones(len(idx))
            continue
        steps = rng.normal(0, 0.004, len(idx))
        out[c] = lvl * np.exp(np.cumsum(steps))
    return pd.DataFrame(out, index=idx)


def pair(hist: pd.DataFrame, base: str, quote: str) -> pd.Series:
    """Price of 1 BASE expressed in QUOTE."""
    return (hist[quote] / hist[base]).rename(f"{base}/{quote}")


def rate(rates: dict, base: str, quote: str) -> float:
    return rates[quote] / rates[base]


def convert(amount: float, base: str, quote: str, rates: dict) -> float:
    return amount * rate(rates, base, quote)
