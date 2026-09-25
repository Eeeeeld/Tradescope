"""Persistent user settings (saved to data/settings.json)."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULTS = {
    "language": "en",            # en | zh | id
    "base": "TWD",               # default conversion: 1 TWD -> IDR
    "quote": "IDR",
    "watchlist": ["IDR", "USD", "JPY", "CNY", "SGD", "MYR", "EUR"],
    "alerts": [
        # pair is BASE/QUOTE, i.e. price of 1 BASE in QUOTE
        {"pair": "TWD/IDR", "condition": "above", "value": 540.0, "enabled": True},
    ],
    "default_range": "3M",
}


def load() -> dict:
    data = dict(DEFAULTS)
    try:
        if SETTINGS_FILE.exists():
            data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return data


def save(settings: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
