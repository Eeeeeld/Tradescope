"""Taiwan–Indonesia trade data.

1. Annual totals: data/trade_tw_id_annual.csv (editable in the app).
   Seeded from Taiwan's Bureau of Foreign Trade (BOFT) Indonesia country file.
2. Product detail: UN Comtrade public preview API (no key needed, 1 period per call).
   Taiwan is not a UN reporter, so we use Indonesia's (mirror) statistics with
   partner code 490 ("Other Asia, nes" = Taiwan in UN data):
     Indonesia imports from Taiwan  (flow M)  ~ Taiwan exports to Indonesia
     Indonesia exports to Taiwan    (flow X)  ~ Taiwan imports from Indonesia
"""
from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from .settings import DATA_DIR

ANNUAL_CSV = DATA_DIR / "trade_tw_id_annual.csv"
COMTRADE = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
INDONESIA, TAIWAN = 360, 490

# Main products in 2024 according to BOFT (keys translated in i18n).
MAIN_EXPORTS = ["prod_memory", "prod_semis", "prod_gasoline", "prod_alloy_steel", "prod_synthetic_knit"]
MAIN_IMPORTS = ["prod_coal", "prod_natgas", "prod_stainless", "prod_nickel", "prod_copper"]


def load_annual() -> pd.DataFrame:
    df = pd.read_csv(ANNUAL_CSV)
    df = df.dropna(subset=["year"]).sort_values("year")
    df["year"] = df["year"].astype(int)
    df["total"] = df["tw_exports_usd_m"] + df["tw_imports_usd_m"]
    df["balance"] = df["tw_exports_usd_m"] - df["tw_imports_usd_m"]
    df["total_yoy"] = df["total"].pct_change() * 100
    df["exports_yoy"] = df["tw_exports_usd_m"].pct_change() * 100
    df["imports_yoy"] = df["tw_imports_usd_m"].pct_change() * 100
    return df.reset_index(drop=True)


def save_annual(df: pd.DataFrame) -> None:
    cols = ["year", "tw_exports_usd_m", "tw_imports_usd_m", "source"]
    df[cols].dropna(subset=["year"]).sort_values("year").to_csv(ANNUAL_CSV, index=False)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def comtrade(year: int, flow: str, cmd: str = "AG2") -> tuple[pd.DataFrame, str | None]:
    """flow: 'M' (Indonesia imports from Taiwan) or 'X' (Indonesia exports to Taiwan).
    cmd: 'AG2' for all HS chapters, or a specific HS code such as '8542'."""
    params = {
        "reporterCode": INDONESIA, "partnerCode": TAIWAN, "period": year,
        "flowCode": flow, "cmdCode": cmd, "partner2Code": 0,
        "customsCode": "C00", "motCode": 0, "includeDesc": "true",
    }
    try:
        r = requests.get(COMTRADE, params=params, timeout=20)
        r.raise_for_status()
        rows = r.json().get("data") or []
    except (requests.RequestException, ValueError) as e:
        return pd.DataFrame(), str(e)
    if not rows:
        return pd.DataFrame(), None
    df = pd.DataFrame(rows)
    keep = [c for c in ["cmdCode", "cmdDesc", "primaryValue"] if c in df.columns]
    df = df[keep].groupby(["cmdCode", "cmdDesc"], as_index=False)["primaryValue"].sum()
    df = df[df["cmdCode"] != "TOTAL"].sort_values("primaryValue", ascending=False)
    return df.reset_index(drop=True), None
