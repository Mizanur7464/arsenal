"""Buyer UI filters on Arsenal eTicketing (Ticket Exchange, seats together)."""

from playwright.sync_api import Page

from .logger_setup import sub, sub_ok, sub_warn

EXCHANGE_PHRASES = (
    "ticket exchange",
    "include ticket exchange",
    "ticketexchange",
    "exchange tickets",
    "show ticket exchange",
)

SEATS_TOGETHER_PHRASES = (
    "seats together",
    "seat together",
    "sitting together",
    "adjacent seats",
)


def _click_associated_control(page: Page, phrase: str) -> bool:
    """Turn on a checkbox/switch found via label or nearby text."""
    locators = [
        page.locator(f'label:has-text("{phrase}")').first,
        page.get_by_label(phrase, exact=False),
        page.locator(f'[aria-label*="{phrase}" i]').first,
        page.locator(f'label:has-text("{phrase}" i) input[type="checkbox"]').first,
        page.locator(f'label:has-text("{phrase}" i) input[type="radio"]').first,
    ]
    for loc in locators:
        try:
            if not loc.is_visible(timeout=1500):
                continue
            tag = loc.evaluate("el => el.tagName.toLowerCase()")
            if tag == "input":
                checked = loc.is_checked()
                if not checked:
                    loc.check(force=True)
                sub_ok(f'Filter ON: "{phrase}" (checkbox)')
                return True
            inp = loc.locator('input[type="checkbox"]').first
            if inp.count() and inp.is_visible(timeout=500):
                if not inp.is_checked():
                    inp.check(force=True)
                sub_ok(f'Filter ON: "{phrase}" (label checkbox)')
                return True
            loc.click()
            sub_ok(f'Filter ON: "{phrase}" (click label)')
            return True
        except Exception:
            continue
    return False


def _try_phrases(
    page: Page, phrases: tuple[str, ...], enabled: bool, *, allow_short_parts: bool = True
) -> bool:
    if not enabled:
        return False
    for phrase in phrases:
        if _click_associated_control(page, phrase):
            return True
        if not allow_short_parts:
            continue
        short = phrase.split()[-2:] if len(phrase.split()) > 2 else (phrase,)
        for part in short:
            if len(part) < 6:
                continue
            if _click_associated_control(page, part):
                return True
    return False


def _try_ticket_exchange(page: Page) -> bool:
    """Full phrases only — never click generic 'ticket' labels."""
    for phrase in EXCHANGE_PHRASES:
        if _click_associated_control(page, phrase):
            return True
    for sel in (
        'label:has-text("Ticket Exchange" i)',
        '[aria-label*="Ticket Exchange" i]',
    ):
        try:
            loc = page.locator(sel).first
            if not loc.is_visible(timeout=1500):
                continue
            inp = loc.locator('input[type="checkbox"]').first
            if inp.is_visible(timeout=500):
                if not inp.is_checked():
                    inp.check(force=True)
                sub_ok("Ticket Exchange ON (checkbox)")
                return True
        except Exception:
            continue
    try:
        cb = page.get_by_role("checkbox", name="Ticket Exchange").first
        if cb.is_visible(timeout=2000):
            if not cb.is_checked():
                cb.check(force=True)
            sub_ok("Ticket Exchange ON (role=checkbox)")
            return True
    except Exception:
        pass
    return False


def _apply_on_roots(page: Page, apply_fn) -> bool:
    if apply_fn(page):
        return True
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            if apply_fn(frame):
                return True
        except Exception:
            continue
    return False


def apply_event_page_filters(page: Page, config: dict) -> dict:
    """
    Apply Ticket Exchange + seats together on the live page when controls exist.
    Returns {"ticket_exchange": bool, "seats_together": bool}.
    """
    f = config.get("filters", {})
    want_tx = bool(f.get("ticket_exchange", False))
    want_seats = bool(f.get("seats_together", False))
    result = {"ticket_exchange": False, "seats_together": False}

    if want_tx:
        sub("Turning ON Ticket Exchange filter on page...")
        if _apply_on_roots(page, _try_ticket_exchange):
            result["ticket_exchange"] = True
            page.wait_for_timeout(800)
        else:
            sub_warn("Ticket Exchange toggle not found (check filter panel on page)")

    if want_seats:
        sub("Turning ON seats-together preference on page...")
        if _try_phrases(page, SEATS_TOGETHER_PHRASES, True):
            result["seats_together"] = True
            page.wait_for_timeout(800)
        else:
            sub_warn("Seats-together control not found (will prefer matching rows in scan)")

    return result
