"""Phase 5 — end-to-end test, handover report, delivery zip."""

import zipfile
import traceback
from datetime import datetime
from pathlib import Path

from .config_loader import load_config, ROOT
from .logger_setup import (
    banner,
    divider,
    step,
    sub,
    sub_ok,
    sub_warn,
    sub_err,
    ok,
    warn,
    err,
    hint,
)
from .browser import launch_browser, close_browser, screenshot, ensure_output_dir, goto
from .auth import dismiss_cookie_and_overlays
from .session import navigate_to_event, wait_through_queue
from .page_filters import apply_event_page_filters
from .page_state import detect_page_state, is_real_event_ticket_page, is_queue_page
from .filters import apply_filters, filter_reason
from .tickets import (
    scan_ticket_options,
    set_quantity,
    try_add_to_basket_and_alert,
    stop_before_checkout,
)
from .telegram_bot import configured_full as _configured
from .bot_state import load_state, note_run, set_monitoring
from .phase1 import check_phase1
import time

SKIP_ZIP_DIRS = {"venv", "__pycache__", ".git", "output"}
SKIP_ZIP_FILES = {".env"}
TOTAL_STEPS = 8


def _collect_output_reports() -> list[str]:
    out = ROOT / "output"
    if not out.is_dir():
        return []
    return [f"  - {p.name}" for p in sorted(out.glob("*.txt"))]


def _scan_and_try_basket(
    page,
    config: dict,
    env: dict,
    *,
    event_id: int,
    event: dict,
    filters: dict,
    nav: str,
) -> dict:
    """Shared ticket scan + basket alert when on event page."""
    partial = {
        "tickets_found": 0,
        "tickets_passed": 0,
        "quantity_set": False,
        "telegram_sent": False,
        "ok": False,
    }
    state = detect_page_state(page)
    partial["page_state"] = state.label
    sub(f"State: {state.label} — {state.details}")
    if state.label == "SOLD_OUT":
        sub_warn("Sold out text on page — still trying seat-map for re-releases")

    from .seat_map import wait_for_ticket_ui, count_map_targets

    wait_for_ticket_ui(page, config)
    n_targets = count_map_targets(page)
    if n_targets:
        sub(f"Seat-map targets on page: {n_targets}")

    step(6, TOTAL_STEPS, "Scan tickets, filters, quantity, basket alert")
    ui_filters = apply_event_page_filters(page, config)
    sub(
        f"Page UI: exchange={'ON' if ui_filters.get('ticket_exchange') else 'not found'} | "
        f"seats={'ON' if ui_filters.get('seats_together') else 'not found'}"
    )
    sub(
        f"Filters: qty={filters.get('quantity')} | "
        f"seats_together={filters.get('seats_together')} | "
        f"ticket_exchange={filters.get('ticket_exchange')} | "
        f"max_price={filters.get('max_price')} | sections={filters.get('sections') or 'any'}"
    )
    options = scan_ticket_options(page, event_id=event_id)
    partial["tickets_found"] = len(options)
    sub(f"Found {len(options)} price/row on page")
    if not options:
        sub_warn("No list prices — seat-map picker will run if seats appear")
    partial["tickets_passed"] = sum(1 for o in options if apply_filters(config, o.to_dict()))
    sub_ok(f"{partial['tickets_passed']}/{partial['tickets_found']} passed filters")

    qty = int(filters.get("quantity", 1))
    sub(f"Trying quantity = {qty}")
    partial["quantity_set"] = set_quantity(page, qty)
    if env["dry_run"]:
        sub("DRY_RUN=true — will NOT click buy / checkout")

    step(7, TOTAL_STEPS, "Basket + Telegram alert")
    event_name = event.get("name") or f"Event {event_id}"
    basket_ok = try_add_to_basket_and_alert(
        page,
        config,
        env["dry_run"],
        event_name=event_name,
        event_id=event_id,
    )
    partial["telegram_sent"] = basket_ok and _configured()
    if basket_ok:
        sub_ok("Ticket match + alert step done")
    else:
        sub_warn("No seat picked yet — monitoring continues")
    stop_before_checkout(page, env["dry_run"])
    partial["ok"] = nav in ("event", "site") or is_real_event_ticket_page(page, event_id)
    return partial


def _run_e2e_core(
    page,
    config: dict,
    env: dict,
    *,
    navigate: bool = True,
) -> dict:
    """Full login/navigation once, or refresh event URL during monitoring."""
    result = {
        "login": False,
        "navigation": "failed",
        "page_state": "UNKNOWN",
        "tickets_found": 0,
        "tickets_passed": 0,
        "quantity_set": False,
        "dry_run": env["dry_run"],
        "url": "",
        "ok": False,
        "telegram_sent": False,
    }

    site = config.get("site", {})
    event = config.get("test_event", {})
    filters = config.get("filters", {})
    event_id = int(event.get("event_id") or 3774)
    timeout = env["page_timeout_ms"]
    queue_wait_ms = int(config.get("retry", {}).get("queue_wait_seconds", 180)) * 1000
    event_url = (event.get("url") or "").strip()
    nav = "failed"

    try:
        if not navigate:
            from .seat_map import soft_refresh_event_page

            soft_refresh_event_page(page, event_url, timeout, config)
            result["url"] = page.url
            result["login"] = True
            nav = "event" if is_real_event_ticket_page(page, event_id) else "site"
            result["navigation"] = nav
            if is_real_event_ticket_page(page, event_id):
                scan = _scan_and_try_basket(
                    page, config, env, event_id=event_id, event=event, filters=filters, nav=nav
                )
                result.update(scan)
                screenshot(page, "phase5_monitor")
            else:
                sub_warn(f"Refresh — not on event {event_id} yet")
            return result

        step(4, TOTAL_STEPS, "Login to Arsenal eTicketing")
        sub(f"Account: {env['account_email'][:3]}***{env['account_email'][-10:]}")
        nav = navigate_to_event(
            page,
            base_url=site.get("base_url", ""),
            queue_url=(event.get("queue_url") or "").strip(),
            event_url=(event.get("url") or "").strip(),
            event_id=event_id,
            email=env["account_email"],
            password=env["account_password"],
            timeout_ms=timeout,
            queue_wait_ms=queue_wait_ms,
        )
        result["navigation"] = nav
        result["login"] = nav != "failed"
        result["url"] = page.url

        if nav == "failed":
            sub_err("Login or navigation failed")
            hint("Check .env email/password or complete 2FA in browser")
        elif nav == "event":
            sub_ok(f"On event page | {page.url[:80]}")
        else:
            sub_warn(f"On Arsenal site (not event {event_id}) | {page.url[:80]}")
            hint("Queue may be closed — sale might not be active")

        step(5, TOTAL_STEPS, "Detect page state (queue / captcha / sold out)")
        state = detect_page_state(page)
        result["page_state"] = state.label
        sub(f"State: {state.label} — {state.details}")
        if state.label == "CAPTCHA":
            sub_warn("Captcha detected — complete manually if browser is visible")
        elif state.label == "QUEUE" or is_queue_page(page):
            sub_warn("Still in queue — waiting longer...")
            if wait_through_queue(page, event_id, queue_wait_ms):
                state = detect_page_state(page)
                if is_real_event_ticket_page(page, event_id):
                    sub_ok("Queue passed — on real Arsenal ticket page")
                else:
                    sub_warn(f"Queue wait ended but still not on ticket page ({state.label})")
            else:
                sub_warn("Still in queue — retry when sale opens")
                hint("When sale is live, wait in browser until you see prices/sections")

        on_ticket_page = is_real_event_ticket_page(page, event_id)
        if not on_ticket_page:
            step(6, TOTAL_STEPS, "Scan tickets — skipped (not on ticket page yet)")
            sub_warn(
                f"No ticket scan — not on event {event_id} ticket listing yet (queue/home/login)"
            )
            hint("This is normal until sale opens and queue lets you through")
            result["tickets_found"] = 0
            result["tickets_passed"] = 0
            screenshot(page, "phase5_e2e_final")
            sub_ok("Screenshot saved to output/")
            result["ok"] = result["login"]
            return result

        scan = _scan_and_try_basket(
            page, config, env, event_id=event_id, event=event, filters=filters, nav=nav
        )
        result.update(scan)
        screenshot(page, "phase5_e2e_final")
        sub_ok("Screenshot saved to output/")
        result["ok"] = result["login"] and (result.get("ok") or nav in ("event", "site"))

    except Exception as e:
        result["error"] = str(e)
        result["ok"] = False
        sub_err(f"Exception: {e}")
        sub("Traceback (last 3 lines):")
        for line in traceback.format_exc().strip().split("\n")[-3:]:
            sub(line)
        try:
            screenshot(page, "phase5_error")
            sub_ok("Error screenshot saved")
        except Exception:
            pass

    return result


def _run_e2e(config: dict, env: dict, *, keep_browser: bool = False):
    """Launch browser, run one cycle; optionally return session for monitoring."""
    timeout = env["page_timeout_ms"]
    if keep_browser:
        step(3, TOTAL_STEPS, "Launch browser (monitoring — session stays open)")
    else:
        step(3, TOTAL_STEPS, "Launch browser (Playwright Chromium)")
    sub(f"HEADLESS={env['headless']} | TIMEOUT={timeout}ms")
    pw, browser, page = launch_browser(env["headless"])
    sub_ok("Browser opened")
    try:
        result = _run_e2e_core(page, config, env, navigate=True)
    except Exception as e:
        result = {"ok": False, "error": str(e)}
        sub_err(str(e))
    finally:
        if keep_browser:
            sub_ok("Browser kept open for monitoring loop")
            return result, (pw, browser, page)
        sub("Closing browser in 3 seconds...")
        if not env["headless"]:
            page.wait_for_timeout(3000)
        close_browser(pw, browser)
        sub_ok("Browser closed")
    return result


def _write_handover_report(e2e: dict, phase1_ok: bool) -> Path:
    ensure_output_dir()
    path = ROOT / "output" / f"phase5_handover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    lines = [
        "=" * 60,
        "ARSENAL BOT — PHASE 5 HANDOVER REPORT",
        datetime.now().isoformat(),
        "=" * 60,
        "",
        f"Phase 1 config: {'PASS' if phase1_ok else 'FAIL'}",
        f"Login: {'OK' if e2e.get('login') else 'FAIL'}",
        f"Navigation: {e2e.get('navigation')}",
        f"Page state: {e2e.get('page_state')}",
        f"URL: {e2e.get('url', '')}",
        f"Tickets: {e2e.get('tickets_passed')}/{e2e.get('tickets_found')} passed filters",
        f"Quantity set: {e2e.get('quantity_set')}",
        f"DRY_RUN: {e2e.get('dry_run')}",
        f"E2E: {'PASS' if e2e.get('ok') else 'PARTIAL/FAIL'}",
    ]
    if e2e.get("error"):
        lines.append(f"Error: {e2e['error']}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _create_delivery_zip() -> Path | None:
    zip_path = ROOT / "arsenal-bot-delivery.zip"
    count = 0
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in ROOT.rglob("*"):
                if path.is_dir():
                    continue
                rel = path.relative_to(ROOT)
                if rel.parts[0] in SKIP_ZIP_DIRS or path.name in SKIP_ZIP_FILES:
                    continue
                if "__pycache__" in rel.parts:
                    continue
                zf.write(path, rel)
                count += 1
        sub_ok(f"Zip created: {zip_path.name} ({count} files, {zip_path.stat().st_size // 1024} KB)")
        return zip_path
    except Exception as e:
        sub_err(f"Zip failed: {e}")
        return None


def _monitor_loop(config: dict, env: dict, session: tuple) -> None:
    """Reuse one browser — refresh event page each cycle instead of full relaunch."""
    delay = float(config.get("retry", {}).get("delay_seconds", 5))
    pw, browser, page = session
    sub_ok("Monitoring ON — press /stop in Telegram or Ctrl+C here to stop")
    try:
        while load_state().get("monitoring"):
            note_run()
            sub("--- Monitor cycle: refresh event page (Telegram /stop to pause) ---")
            _run_e2e_core(page, config, env, navigate=False)
            if not load_state().get("monitoring"):
                break
            sub(f"Waiting {delay}s before next search...")
            time.sleep(delay)
    finally:
        sub("Closing monitoring browser...")
        close_browser(pw, browser)
        sub_ok("Browser closed")
    sub_ok("Monitoring loop ended")


def run_phase5() -> bool:
    import os
    from .bot_state import set_monitoring

    banner("Arsenal Bot — FINAL", "Ticket search + Telegram commands")
    divider("FINAL RUN — follow each STEP below")

    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("AUTO_MONITOR", "").lower() in (
        "1",
        "true",
        "yes",
    ):
        set_monitoring(True)
        sub_ok("Cloud deploy — monitoring auto-started (Telegram /stop to pause)")

    step(1, TOTAL_STEPS, "Load config.yaml and .env")
    config = load_config()
    env = config["_env"]
    sub_ok("config.yaml loaded")

    from .telegram_bot import configured, start_listener_background, keep_listening_until_ctrl_c, test_connection

    telegram_api_ok = False
    if configured():
        telegram_api_ok = test_connection()
        if telegram_api_ok:
            start_listener_background()
        else:
            sub_warn("Telegram /start will NOT reply until VPN fixes API access")
    else:
        sub_warn("TELEGRAM_BOT_TOKEN missing — no Telegram")

    sub(f"Event: {config.get('test_event', {}).get('name', '?')}")
    sub(f"Event ID: {config.get('test_event', {}).get('event_id', '?')}")
    sub(f"DRY_RUN={env['dry_run']} | HEADLESS={env['headless']}")

    from .captcha_solver import configured as captcha_ready

    if captcha_ready():
        sub_ok("2captcha API key found — Queue-it captcha can be solved automatically")
    else:
        sub_warn("TWOCAPTCHA_API_KEY not in .env — solve queue captcha manually in browser")

    sub_ok("Browser session saved in data/browser_profile/ (login persists between runs)")

    if not env.get("account_email") or not env.get("account_password"):
        sub_err("Missing ACCOUNT_EMAIL or ACCOUNT_PASSWORD in .env")
        hint("Open .env and add buyer login — then run again")
        err("STOPPED at STEP 1 — fix .env first")
        return False
    sub_ok(".env has login credentials")

    step(2, TOTAL_STEPS, "Pre-flight checks (files, URLs, docs)")
    phase1_ok = check_phase1()
    if phase1_ok:
        sub_ok("All Phase 1 checks passed")
    else:
        sub_warn("Some Phase 1 checks failed — read messages above")

    note_run()
    monitoring = load_state().get("monitoring")
    if monitoring:
        e2e, session = _run_e2e(config, env, keep_browser=True)
    else:
        e2e = _run_e2e(config, env)
        session = None

    if load_state().get("monitoring") and session:
        divider("MONITORING MODE")
        hint("Use Telegram /stop to end, or Ctrl+C in this window")
        try:
            _monitor_loop(config, env, session)
        except KeyboardInterrupt:
            set_monitoring(False)
            sub_warn("Stopped by user (Ctrl+C)")

    step(8, TOTAL_STEPS, "Save handover report and delivery zip")
    report_path = _write_handover_report(e2e, phase1_ok)
    sub_ok(f"Report: output/{report_path.name}")
    _create_delivery_zip()

    divider("FINAL RESULT")
    success = False
    if e2e.get("ok") and phase1_ok:
        ok("SUCCESS — Phase 5 COMPLETE. Ready to send to buyer.")
        hint("Send: arsenal-bot-delivery.zip + output/*.png + BUYER_DELIVERY_MESSAGE.txt")
        success = True
    elif e2e.get("login"):
        warn("PARTIAL SUCCESS — login works; event/queue may be closed.")
        hint("Still send zip + screenshots + explain queue/sale timing to buyer")
        success = True
    else:
        err("FAILED — fix .env or check output/ screenshots")

    if telegram_api_ok:
        keep_listening_until_ctrl_c()
    elif os.getenv("RAILWAY_ENVIRONMENT"):
        sub_warn("Telegram not connected — staying alive for Railway (check Variables)")
        keep_listening_until_ctrl_c()
    else:
        divider("TELEGRAM NOT CONNECTED")
        hint("Ticket scan done. Fix VPN, then run python run.py again for /start")
    return success


if __name__ == "__main__":
    raise SystemExit(0 if run_phase5() else 1)
