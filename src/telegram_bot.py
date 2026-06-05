"""Telegram command bot: /start, /status, /start_on, /stop + alerts."""

import json
import os
import threading
import time
import urllib.parse
import urllib.request

from .bot_state import load_state, set_monitoring, save_state
from .config_loader import load_config, ROOT
from .logger_setup import sub, sub_ok, sub_warn, sub_err, err, divider, hint

API = "https://api.telegram.org/bot{token}/{method}"
_listener_started = False
_listener_lock = threading.Lock()
_last_api_warn = 0.0
_api_connected = False

WELCOME_TEXT = """Welcome to Arsenal Ticket Bot

I watch Arsenal eTicketing for you and send an alert when tickets are added to the basket. You complete payment yourself.

Commands:
/start - This welcome message
/status - See if monitoring is on
/start_on - Start searching for tickets
/stop - Stop searching

Setup: seller runs the bot on PC with your login in .env file.
Safety: DRY_RUN mode can be enabled for testing (no real purchase).

Chelsea bot = separate project later."""


def _token() -> str:
    return (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()


def _open_access() -> bool:
    """When true, anyone can use /start_on /stop /status (default: open)."""
    val = (os.getenv("TELEGRAM_OPEN_ACCESS") or "true").strip().lower()
    return val in ("1", "true", "yes", "on")


def _alert_chat_ids() -> list[str]:
    """
    Chats that receive basket alerts (TELEGRAM_CHAT_IDS / TELEGRAM_CHAT_ID).
    Commands are open to everyone when TELEGRAM_OPEN_ACCESS=true.
    """
    ids: list[str] = []
    multi = (os.getenv("TELEGRAM_CHAT_IDS") or "").strip()
    if multi:
        for part in multi.replace(" ", "").split(","):
            part = part.strip()
            if part and part not in ids:
                ids.append(part)
    single = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if single and single not in ids:
        ids.append(single)
    if not ids:
        st = load_state()
        saved = str(st.get("telegram_chat_id") or "").strip()
        if saved:
            ids.append(saved)
    return ids


def _allowed_chat_ids() -> list[str]:
    """Alias for alert destinations."""
    return _alert_chat_ids()


def _chat_id() -> str:
    """First alert chat (backward compatible)."""
    ids = _alert_chat_ids()
    return ids[0] if ids else ""


def _is_allowed_chat(chat_id: str) -> bool:
    if _open_access():
        return True
    allowed = _alert_chat_ids()
    if not allowed:
        return True
    return str(chat_id) in allowed


def configured() -> bool:
    """True if bot token exists (listener can run)."""
    return bool(_token())


def configured_full() -> bool:
    """True if token + at least one chat id (alerts can send)."""
    return bool(_token() and _alert_chat_ids())


def test_connection() -> bool:
    """One clear test — can this PC reach Telegram API?"""
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    if not _token():
        sub_err("TELEGRAM_BOT_TOKEN missing in .env")
        return False
    if not _alert_chat_ids():
        sub_warn("TELEGRAM_CHAT_ID / TELEGRAM_CHAT_IDS empty — basket alerts need these")
    sub("Testing api.telegram.org from this PC...")
    if _prepare_telegram():
        sub_ok("Telegram API OK — /start will work when listener is running")
        return True
    err("MAIN PROBLEM: This PC cannot reach api.telegram.org (timeout/blocked)")
    hint("Telegram app on phone works, but the BOT needs PC -> api.telegram.org")
    hint("Fix: turn ON VPN on this computer, then run python run.py again")
    hint("Or set TELEGRAM_PROXY= in .env if you use a proxy")
    return False


def _urlopen(req: urllib.request.Request, timeout: int = 40):
    proxy = (os.getenv("TELEGRAM_PROXY") or os.getenv("HTTPS_PROXY") or "").strip()
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
        return opener.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


def _api(method: str, *, quiet: bool = False, **params) -> dict | None:
    global _last_api_warn, _api_connected
    token = _token()
    if not token:
        return None
    url = API.format(token=token, method=method)
    if method in ("sendMessage", "setMyCommands"):
        body = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, method="POST", headers={"Content-Type": "application/json"}
        )
    else:
        qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        req = urllib.request.Request(f"{url}?{qs}")
    try:
        with _urlopen(req, timeout=40) as resp:
            _api_connected = True
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        _api_connected = False
        if not quiet:
            now = time.time()
            if now - _last_api_warn > 30:
                _last_api_warn = now
                sub_warn(f"Telegram API unreachable ({method}): {e}")
                hint("Bangladesh/network: turn ON VPN, or add TELEGRAM_PROXY= in .env")
        return None


def _prepare_telegram() -> bool:
    """Remove webhook (blocks polling) and show bot username."""
    _api("deleteWebhook", quiet=True)
    me = _api("getMe", quiet=True)
    if me and me.get("ok"):
        user = me["result"].get("username", "?")
        sub_ok(f"Telegram connected: @{user}")
        return True
    return False


def _send_one(text: str, cid: str) -> bool:
    if not _token() or not cid:
        return False
    try:
        chat_param = int(cid) if str(cid).lstrip("-").isdigit() else cid
    except ValueError:
        chat_param = cid
    r = _api("sendMessage", chat_id=chat_param, text=text)
    if r and r.get("ok"):
        return True
    desc = (r or {}).get("description", "unknown error")
    sub_warn(f"Telegram send failed to {cid}: {desc}")
    return False


def send_message(text: str, chat_id: str | None = None) -> bool:
    """Reply to one chat, or broadcast basket alerts to all TELEGRAM_CHAT_IDS."""
    if chat_id:
        return _send_one(text, chat_id)
    targets = _alert_chat_ids()
    if not _token() or not targets:
        sub_warn("send_message failed — missing token or chat_id(s)")
        return False
    ok = False
    for cid in targets:
        if _send_one(text, cid):
            ok = True
    if ok and len(targets) > 1:
        sub_ok(f"Alert sent to {len(targets)} chats")
    return ok


def _register_commands() -> None:
    _api(
        "setMyCommands",
        commands=[
            {"command": "start", "description": "Welcome message"},
            {"command": "status", "description": "Bot status"},
            {"command": "start_on", "description": "Start ticket monitoring"},
            {"command": "stop", "description": "Stop monitoring"},
        ],
    )


def _status_text() -> str:
    st = load_state()
    config = load_config()
    env = config["_env"]
    event = config.get("test_event", {})
    on = "ON" if st.get("monitoring") else "OFF"
    lines = [
        "Arsenal Ticket Bot — Status",
        "",
        f"Monitoring: {on}",
        f"DRY_RUN: {env.get('dry_run')}",
        f"Event: {event.get('name', 'not set')}",
        f"Quantity: {config.get('filters', {}).get('quantity', '?')}",
        f"Seats together: {config.get('filters', {}).get('seats_together', '?')}",
        f"Ticket exchange: {config.get('filters', {}).get('ticket_exchange', '?')}",
        "",
        f"Last run: {st.get('last_run') or 'never'}",
        f"Last alert: {st.get('last_alert') or 'never'}",
        "",
        st.get("last_message", ""),
    ]
    return "\n".join(lines)


def _print_start_user_info(msg: dict, chat_id: str) -> None:
    """Show Telegram IDs in terminal when someone sends /start."""
    user = msg.get("from") or {}
    user_id = user.get("id", "?")
    username = (user.get("username") or "").strip()
    name = " ".join(
        x for x in (user.get("first_name"), user.get("last_name")) if x
    ).strip() or "—"
    uname = f"@{username}" if username else "(no username)"
    alerts = _alert_chat_ids()
    if _open_access():
        role = "OPEN — all commands work"
        if alerts and str(chat_id) in alerts:
            role += " | also gets basket alerts"
        elif alerts:
            role += " | basket alerts go to .env list only"
    elif _is_allowed_chat(chat_id):
        role = f"ALLOWED ({len(alerts)} alert chat(s) in .env)"
    else:
        role = f"RESTRICTED — not in .env ({', '.join(alerts)})"
    sub_ok(
        f"TELEGRAM /start — chat_id={chat_id} | user_id={user_id} | {uname} | {name} | {role}"
    )
    if str(chat_id) not in alerts:
        hint(f"For basket alerts add: TELEGRAM_CHAT_IDS={chat_id}")


def _handle_command(text: str, chat_id: str) -> None:
    cmd = text.strip().split()[0].lower().split("@")[0]
    if cmd not in ("/start", "/help"):
        sub(f"Telegram command received: {cmd} from chat {chat_id}")

    if cmd in ("/start", "/help"):
        send_message(WELCOME_TEXT, chat_id)
        save_state(last_message="User ran /start")
    elif cmd == "/status":
        send_message(_status_text(), chat_id)
    elif cmd == "/start_on":
        set_monitoring(True)
        send_message(
            "Monitoring is ON.\n\n"
            "The bot will keep searching for tickets on your configured event.\n"
            "You will get a Telegram alert when tickets are added to the basket.\n\n"
            "Use /stop to pause.",
            chat_id,
        )
    elif cmd == "/stop":
        set_monitoring(False)
        send_message(
            "Monitoring is OFF.\n\nTicket search paused. Use /start_on when you want to resume.",
            chat_id,
        )
    else:
        send_message(
            "Unknown command.\n\nUse /start for help, /status, /start_on, or /stop.",
            chat_id,
        )


def _poll_loop() -> None:
    if not configured():
        return

    st = load_state()
    offset = int(st.get("telegram_offset") or 0)
    commands_registered = False

    while True:
        if not _prepare_telegram():
            time.sleep(15)
            continue
        if not commands_registered:
            _register_commands()
            commands_registered = True
            sub_ok("Telegram ready — send /start in your bot chat now")
            ids = _alert_chat_ids()
            if _open_access():
                sub_ok("Telegram commands OPEN — anyone can use /start_on /stop /status")
            else:
                sub("Telegram commands RESTRICTED to .env chat list only")
            sub(
                f"Basket alert chat_id(s): {', '.join(ids) if ids else 'none — set TELEGRAM_CHAT_IDS'}"
            )

        try:
            r = _api("getUpdates", offset=offset, timeout=25, quiet=True)
            if not r or not r.get("ok"):
                if r:
                    sub_warn(f"getUpdates: {(r.get('description') or r)[:80]}")
                else:
                    _prepare_telegram()
                time.sleep(5)
                continue
            for upd in r.get("result", []):
                offset = upd["update_id"] + 1
                save_state(telegram_offset=offset)
                msg = upd.get("message") or {}
                text = (msg.get("text") or "").strip()
                chat = msg.get("chat") or {}
                cid = str(chat.get("id", ""))
                if not text or not cid:
                    continue

                if not _alert_chat_ids() and not _open_access():
                    save_state(telegram_chat_id=cid)
                    sub_ok(
                        f"Saved chat ID: {cid} — add TELEGRAM_CHAT_IDS={cid} to .env"
                    )

                if text.startswith("/"):
                    cmd = text.strip().split()[0].lower().split("@")[0]
                    if cmd in ("/start", "/help") and msg:
                        _print_start_user_info(msg, cid)
                    if not _is_allowed_chat(cid):
                        sub_warn(
                            f"Ignored {cmd} from chat {cid} "
                            f"(set TELEGRAM_OPEN_ACCESS=true or add to TELEGRAM_CHAT_IDS)"
                        )
                        continue
                    _handle_command(text, cid)
        except Exception as e:
            sub_warn(f"Telegram poll error: {e}")
            time.sleep(5)


def start_listener_background() -> bool:
    """Start getUpdates polling in a daemon thread (once)."""
    global _listener_started
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    with _listener_lock:
        if _listener_started:
            return True
        if not configured():
            return False
        if not _alert_chat_ids():
            sub_warn("TELEGRAM_CHAT_IDS empty — basket alerts need chat id(s) in .env")
        t = threading.Thread(target=_poll_loop, daemon=True, name="telegram-commands")
        t.start()
        _listener_started = True
        time.sleep(0.5)
        sub("Telegram thread started (connecting to api.telegram.org...)")
        return True


def keep_listening_until_ctrl_c() -> None:
    """Keep program alive so Telegram commands work after ticket scan finishes."""
    if not configured():
        return
    divider("TELEGRAM ACTIVE")
    sub_ok("Ticket scan finished. Bot still listens for Telegram commands.")
    hint("Press Ctrl+C in this window to fully stop")
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        sub_ok("Telegram listener stopped (program exit)")


# Re-export for telegram_alert.py
def send_basket_alert(
    *,
    event_name: str,
    quantity: int,
    page_url: str = "",
    dry_run: bool = True,
    seats_together: bool | None = None,
    ticket_exchange: bool | None = None,
) -> bool:
    from .bot_state import note_alert

    prefix = "[DRY RUN] " if dry_run else ""
    lines = [
        f"{prefix}Tickets in basket ({quantity}) — please pay on eTicketing",
        "",
        f"Event: {event_name}",
    ]
    if seats_together is not None:
        lines.append(f"Seats together: {'YES' if seats_together else 'NO'}")
    if ticket_exchange is not None:
        lines.append(f"Ticket exchange: {'ON' if ticket_exchange else 'OFF'}")
    if page_url:
        lines.append(f"Link: {page_url}")
    lines.append("\nPlease review and purchase on eTicketing yourself.")
    ok = send_message("\n".join(lines))
    if ok:
        note_alert()
    return ok


def send_test_message() -> bool:
    return send_message("Arsenal bot — Telegram test OK.\nTry /start for commands.")
