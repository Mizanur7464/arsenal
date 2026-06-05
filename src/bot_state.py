"""Shared state for Telegram start_on / stop and status."""

import json
from datetime import datetime
from pathlib import Path

from .config_loader import ROOT

STATE_DIR = ROOT / "data"
STATE_FILE = STATE_DIR / "bot_state.json"


def _default() -> dict:
    return {
        "monitoring": False,
        "last_run": None,
        "last_alert": None,
        "last_message": "Bot ready. Use /start_on to begin monitoring.",
        "telegram_offset": 0,
        "telegram_chat_id": None,
    }


def load_state() -> dict:
    if not STATE_FILE.is_file():
        return _default()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return {**_default(), **data}
    except Exception:
        return _default()


def save_state(**kwargs) -> dict:
    STATE_DIR.mkdir(exist_ok=True)
    data = load_state()
    data.update(kwargs)
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def set_monitoring(on: bool) -> dict:
    msg = "Monitoring started." if on else "Monitoring stopped."
    return save_state(monitoring=on, last_message=msg)


def note_run() -> None:
    save_state(last_run=datetime.now().isoformat())


def note_alert() -> None:
    save_state(last_alert=datetime.now().isoformat())
