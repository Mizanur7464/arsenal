"""Shared browser session: login + reach event page."""

import time

from playwright.sync_api import Page

from .auth import ensure_logged_in, is_login_page, wait_for_event_page
from .browser import goto, screenshot
from .logger_setup import sub, sub_ok, sub_warn, hint
from .page_state import detect_page_state, is_real_event_ticket_page, is_queue_page
from .queue_captcha import handle_queue_page, is_queue_closed


def wait_through_queue(
    page: Page,
    event_id: int,
    queue_wait_ms: int,
    *,
    base_url: str = "",
    email: str = "",
    password: str = "",
    timeout_ms: int = 60000,
) -> bool:
    """Stay on queue page until event URL or ticket UI appears."""
    if queue_wait_ms <= 0:
        return False
    sub(f"Waiting in queue up to {queue_wait_ms // 1000}s (sale may need time)...")
    deadline = time.time() + queue_wait_ms / 1000
    poll_ms = 4000
    warned_restricted = False
    while time.time() < deadline:
        if is_queue_closed(page):
            return False

        q = handle_queue_page(page)
        if q == "closed":
            return False

        if email and is_login_page(page):
            ensure_logged_in(page, base_url, email, password, timeout_ms)

        if is_real_event_ticket_page(page, event_id):
            sub_ok(f"Queue passed — real ticket page (event {event_id})")
            return True
        if wait_for_event_page(page, event_id, timeout_ms=poll_ms):
            return True
        if not warned_restricted:
            try:
                title = (page.title() or "").lower()
            except Exception:
                title = ""
            if "restricted" in title:
                sub_warn("Restricted access — use UK VPN on this PC")
                hint("Stay in queue in browser until tickets load, or retry when sale opens")
                warned_restricted = True
        page.wait_for_timeout(poll_ms)
    if is_queue_page(page):
        sub_warn("Still on Queue-it — not the ticket shop page yet")
    return False


def navigate_to_event(
    page: Page,
    *,
    base_url: str,
    queue_url: str,
    event_url: str,
    event_id: int,
    email: str,
    password: str,
    timeout_ms: int,
    queue_wait_ms: int = 180000,
) -> str:
    """
    Returns: 'event' | 'site' | 'failed'
    """
    if not ensure_logged_in(page, base_url, email, password, timeout_ms):
        sub_warn("Login step returned false")
        return "failed"

    screenshot(page, "session_after_login")

    from .config_loader import load_config

    retry_cfg = load_config().get("retry", {})
    skip_queue = bool(retry_cfg.get("skip_queue_when_closed", True))

    if queue_url and not skip_queue:
        sub("Trying buyer queue link...")
        try:
            goto(page, queue_url, timeout_ms, label="queue")
            screenshot(page, "session_queue")
            if is_queue_closed(page):
                sub_warn("Queue closed — skipping queue wait, opening event URL")
            else:
                handle_queue_page(page)
                wait_ms = max(queue_wait_ms, 90000)
                if wait_through_queue(
                    page,
                    event_id,
                    wait_ms,
                    base_url=base_url,
                    email=email,
                    password=password,
                    timeout_ms=timeout_ms,
                ) and is_real_event_ticket_page(page, event_id):
                    return "event"
                sub_warn("Queue did not reach real ticket page in time")
        except Exception as e:
            sub_warn(f"Queue error: {e}")
    elif queue_url and skip_queue:
        sub("Queue skip enabled — opening event URL directly (faster)")

    sub("Opening direct event URL...")
    goto(page, event_url, timeout_ms, label="event")
    page.wait_for_timeout(3000)

    if is_login_page(page):
        ensure_logged_in(page, base_url, email, password, timeout_ms)

    state = detect_page_state(page)
    if state.label == "QUEUE" or is_queue_page(page):
        handle_queue_page(page)
        if wait_through_queue(
            page,
            event_id,
            queue_wait_ms,
            base_url=base_url,
            email=email,
            password=password,
            timeout_ms=timeout_ms,
        ) and is_real_event_ticket_page(page, event_id):
            return "event"

    if wait_for_event_page(page, event_id, timeout_ms=15000):
        return "event"

    if is_real_event_ticket_page(page, event_id):
        return "event"

    if is_login_page(page):
        if ensure_logged_in(page, base_url, email, password, timeout_ms):
            goto(page, event_url, timeout_ms, label="event-retry")
            if is_real_event_ticket_page(page, event_id):
                return "event"

    sub("Searching Buy/Tickets links on page...")
    for sel in (
        f'a[href*="Event/Index/{event_id}"]',
        'a:has-text("Buy")',
        'a:has-text("Tickets")',
        'button:has-text("Find tickets")',
    ):
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=3000):
                loc.click()
                page.wait_for_timeout(3000)
                if wait_for_event_page(page, event_id, timeout_ms=15000):
                    return "event"
                break
        except Exception:
            continue

    if "eticketing.co.uk/arsenal" in page.url:
        return "site"
    return "failed"
