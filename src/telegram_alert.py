"""Telegram alerts — uses telegram_bot.send_message."""

from .telegram_bot import configured_full, send_message, send_basket_alert, send_test_message

configured = configured_full
_configured = configured_full

__all__ = ["configured", "send_message", "send_basket_alert", "send_test_message", "_configured"]
