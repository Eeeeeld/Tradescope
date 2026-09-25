"""Taiwan–Indonesia trade news via Google News RSS (no key needed)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

import pandas as pd
import requests
import streamlit as st

BASE = "https://news.google.com/rss/search"

LOCALES = {  # hl, gl, ceid
    "en": ("en-US", "US", "US:en"),
    "zh": ("zh-TW", "TW", "TW:zh-Hant"),
    "id": ("id", "ID", "ID:id"),
}

CORE_QUERY = {
    "en": 'Taiwan Indonesia (trade OR export OR import OR investment OR tariff)',
    "zh": '台灣 印尼 (貿易 OR 出口 OR 進口 OR 投資 OR 關稅)',
    "id": 'Taiwan Indonesia (perdagangan OR ekspor OR impor OR investasi OR tarif)',
}

# Optional topic narrowing, per news language.
TOPICS = {
    "topic_semis":      {"en": "semiconductor", "zh": "半導體", "id": "semikonduktor"},
    "topic_energy":     {"en": "(coal OR LNG OR energy)", "zh": "(煤 OR 天然氣 OR 能源)", "id": "(batu bara OR LNG OR energi)"},
    "topic_nickel":     {"en": "(nickel OR EV OR battery)", "zh": "(鎳 OR 電動車 OR 電池)", "id": "(nikel OR kendaraan listrik OR baterai)"},
    "topic_workers":    {"en": "migrant workers", "zh": "移工", "id": "pekerja migran"},
    "topic_investment": {"en": "investment", "zh": "投資", "id": "investasi"},
    "topic_policy":     {"en": "(New Southbound OR agreement)", "zh": "(新南向 OR 協定)", "id": "(Kebijakan Arah Selatan Baru OR perjanjian)"},
}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch(lang: str, days: int = 30, topic: str | None = None) -> tuple[pd.DataFrame, str | None]:
    q = CORE_QUERY[lang]
    if topic:
        q += " " + TOPICS[topic][lang]
    q += f" when:{days}d"
    hl, gl, ceid = LOCALES[lang]
    url = f"{BASE}?{urlencode({'q': q, 'hl': hl, 'gl': gl, 'ceid': ceid})}"
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0 TradeScope"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except (requests.RequestException, ET.ParseError) as e:
        return pd.DataFrame(), str(e)

    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        source = (it.findtext("source") or "").strip()
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3]
        try:
            published = parsedate_to_datetime(it.findtext("pubDate") or "")
        except (TypeError, ValueError):
            published = None
        items.append({"title": title, "source": source, "link": it.findtext("link"),
                      "published": published, "lang": lang})
    df = pd.DataFrame(items)
    if not df.empty:
        df["published"] = pd.to_datetime(df["published"], utc=True).dt.tz_convert("Asia/Taipei")
        df = df.sort_values("published", ascending=False).drop_duplicates("title")
    return df.reset_index(drop=True), None
