"""Load settings from config.yaml and .env."""

from pathlib import Path
import os

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def _env_bool(key: str) -> bool | None:
    val = os.getenv(key)
    if val is None or not str(val).strip():
        return None
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _apply_env_filter_overrides(data: dict) -> None:
    """Buyer can set filters in .env (e.g. TICKET_EXCHANGE=true)."""
    filters = data.setdefault("filters", {})
    tx = _env_bool("TICKET_EXCHANGE")
    if tx is not None:
        filters["ticket_exchange"] = tx
    seats = _env_bool("SEATS_TOGETHER")
    if seats is not None:
        filters["seats_together"] = seats


def load_config(path: Path | None = None) -> dict:
    load_dotenv(ROOT / ".env")
    path = path or (ROOT / "config.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _apply_env_filter_overrides(data)
    data["_env"] = {
        "headless": os.getenv("HEADLESS", "false").lower() == "true",
        "page_timeout_ms": int(os.getenv("PAGE_TIMEOUT_MS", "60000")),
        "dry_run": os.getenv("DRY_RUN", "true").lower() == "true",
        "account_email": (os.getenv("ACCOUNT_EMAIL") or "").strip(),
        "account_password": (os.getenv("ACCOUNT_PASSWORD") or "").strip(),
        "telegram_bot_token": (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip(),
        "telegram_chat_id": (os.getenv("TELEGRAM_CHAT_ID") or "").strip(),
        "twocaptcha_api_key": (
            os.getenv("TWOCAPTCHA_API_KEY")
            or os.getenv("CAPTCHA_API_KEY")
            or ""
        ).strip(),
    }
    return data
