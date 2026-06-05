"""Scan ticket listings, apply filters, set quantity, add to basket (dry-run safe)."""

import re
from dataclasses import dataclass

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .filters import apply_filters, filter_reason, rank_ticket_option
from .logger_setup import sub, sub_ok, sub_warn
from .page_filters import apply_event_page_filters

PRICE_RE = re.compile(r"£\s*(\d+(?:\.\d{2})?)")
QUANTITY_SELECTORS = [
    'select[name*="quantity" i]',
    'select[id*="quantity" i]',
    'select[aria-label*="quantity" i]',
    '#quantity',
    'select[name*="qty" i]',
]
QUANTITY_INPUT_SELECTORS = [
    'input[name*="quantity" i]',
    'input[type="number"]',
]
TICKET_ROW_SELECTORS = [
    '[class*="ticket" i]',
    '[class*="price-band" i]',
    '[class*="priceband" i]',
    '[class*="area" i]',
    '[data-testid*="ticket" i]',
    '[class*="listing" i]',
    "table tr",
    '[role="row"]',
    "li",
]
SELECT_BUTTON_SELECTORS = [
    'button:has-text("Select")',
    'button:has-text("Choose")',
    'a:has-text("Select")',
    'button:has-text("Buy")',
    'button:has-text("Add")',
    '[class*="select" i] button',
]
BASKET_SIGNALS = (
    "added to basket",
    "added to your basket",
    "in your basket",
    "basket total",
    "view basket",
    "shopping basket",
    "item in basket",
    "continue to checkout",
)
CHECKOUT_KEYWORDS = ("checkout", "payment", "pay now", "purchase", "confirm order")
QUEUE_NOISE = (
    "why is there a queue",
    "queue-it",
    "your place in line",
    "waiting room",
    "softblock",
    "please wait",
)


def _is_ticket_row_text(text: str) -> bool:
    lower = text.lower()
    if any(n in lower for n in QUEUE_NOISE):
        return False
    price = _parse_price(text)
    return price is not None and price > 0


@dataclass
class TicketOption:
    section: str
    price: float | None
    qty_available: int
    raw_text: str

    def to_dict(self) -> dict:
        return {
            "section": self.section,
            "price": self.price or 0,
            "qty_available": self.qty_available,
            "raw_text": self.raw_text[:200],
        }


def _parse_price(text: str) -> float | None:
    m = PRICE_RE.search(text)
    return float(m.group(1)) if m else None


def scan_ticket_options(page: Page, *, event_id: int | None = None) -> list[TicketOption]:
    """Read visible ticket/price blocks from the current page."""
    from .page_state import is_queue_page, is_real_event_ticket_page

    if is_queue_page(page):
        sub_warn("Still on Queue-it page — skipping ticket scan (not real tickets)")
        return []
    if event_id and not is_real_event_ticket_page(page, event_id):
        sub_warn("Not on Arsenal ticket listing yet — skipping scan")
        return []

    options: list[TicketOption] = []
    seen: set[str] = set()

    for sel in TICKET_ROW_SELECTORS:
        try:
            rows = page.locator(sel)
            count = min(rows.count(), 50)
            for i in range(count):
                row = rows.nth(i)
                try:
                    if not row.is_visible(timeout=500):
                        continue
                    text = row.inner_text(timeout=2000).strip()
                    if len(text) < 4 or text in seen:
                        continue
                    if not _is_ticket_row_text(text):
                        continue
                    seen.add(text)
                    price = _parse_price(text)
                    section = text.split("\n")[0][:60] if text else "Unknown"
                    options.append(
                        TicketOption(
                            section=section,
                            price=price,
                            qty_available=10,
                            raw_text=text,
                        )
                    )
                except Exception:
                    continue
        except Exception:
            continue
        if len(options) >= 8:
            break

    if not options:
        try:
            body = page.locator("body").inner_text(timeout=5000)
        except Exception:
            body = ""
        for line in body.split("\n"):
            line = line.strip()
            if len(line) < 200 and line not in seen and _is_ticket_row_text(line):
                seen.add(line)
                options.append(
                    TicketOption(
                        section=line[:60],
                        price=_parse_price(line),
                        qty_available=10,
                        raw_text=line,
                    )
                )
            if len(options) >= 20:
                break

    return options


def _filter_options(config: dict, options: list[TicketOption]) -> list[TicketOption]:
    passed = [o for o in options if apply_filters(config, o.to_dict(), seats_strict=True)]
    if not passed and options and config.get("filters", {}).get("seats_together"):
        sub_warn("No strict seats-together rows — relaxing to any ticket matching qty/price")
        passed = [o for o in options if apply_filters(config, o.to_dict(), seats_strict=False)]
    passed.sort(key=lambda o: rank_ticket_option(config, o.to_dict()))
    return passed


def set_quantity(page: Page, quantity: int) -> bool:
    sub(f"Setting quantity to {quantity}...")
    for sel in QUANTITY_SELECTORS:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=3000):
                loc.select_option(value=str(quantity))
                sub_ok(f"Quantity set via {sel}")
                return True
        except Exception:
            try:
                loc = page.locator(sel).first
                loc.select_option(label=str(quantity))
                sub_ok(f"Quantity set (label) via {sel}")
                return True
            except Exception:
                continue

    for sel in QUANTITY_INPUT_SELECTORS:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=2000):
                loc.fill(str(quantity))
                sub_ok(f"Quantity filled via {sel}")
                return True
        except Exception:
            continue

    from .seat_map import _set_quantity_stepper

    if _set_quantity_stepper(page, quantity):
        return True
    sub_warn("Quantity control not found (may appear after seat pick)")
    return False


def confirm_in_basket(page: Page) -> bool:
    """Heuristic: basket/cart step reached after select."""
    try:
        url = page.url.lower()
        if "basket" in url or "/cart" in url:
            return True
        body = page.locator("body").inner_text(timeout=4000).lower()
        return any(sig in body for sig in BASKET_SIGNALS)
    except Exception:
        return False


def _click_select_in_row(page: Page, option: TicketOption, dry_run: bool) -> bool:
    """Click Select/Buy on the row that matches the option text."""
    snippet = (option.raw_text or option.section)[:40].strip()
    if not snippet:
        return _click_first_select_button(page, dry_run)

    try:
        row = page.locator(f"text={snippet[:25]}").first
        if row.is_visible(timeout=2000):
            container = row.locator("xpath=ancestor::*[self::tr or self::li or self::motion.div or self::div][1]")
            for sel in SELECT_BUTTON_SELECTORS:
                btn = container.locator(sel).first
                try:
                    if btn.is_visible(timeout=1500):
                        return _click_button(btn, dry_run, page)
                except Exception:
                    continue
    except Exception:
        pass

    if option.price is not None:
        price_snip = f"£{int(option.price)}"
        try:
            row = page.get_by_text(price_snip, exact=False).first
            if row.is_visible(timeout=2000):
                parent = row.locator("xpath=ancestor::tr | ancestor::li | ancestor::motion.div").first
                for sel in SELECT_BUTTON_SELECTORS:
                    btn = parent.locator(sel).first
                    try:
                        if btn.is_visible(timeout=1500):
                            return _click_button(btn, dry_run, page)
                    except Exception:
                        continue
        except Exception:
            pass

    return _click_first_select_button(page, dry_run)


def _click_button(btn, dry_run: bool, page: Page) -> bool:
    if dry_run:
        sub("DRY_RUN: would click ticket select — skipping real click")
        return True
    btn.click()
    page.wait_for_timeout(2500)
    sub_ok("Clicked ticket select button")
    return True


def _click_first_select_button(page: Page, dry_run: bool) -> bool:
    for sel in SELECT_BUTTON_SELECTORS:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=3000):
                return _click_button(btn, dry_run, page)
        except PlaywrightTimeout:
            continue
        except Exception:
            continue
    sub_warn("Ticket match found but no Select/Buy button visible")
    return False


def try_add_to_basket_and_alert(
    page: Page,
    config: dict,
    dry_run: bool,
    *,
    event_name: str = "Arsenal event",
    event_id: int | None = None,
) -> bool:
    """Apply page filters, select ticket, add to basket, Telegram alert immediately."""
    from .page_state import is_real_event_ticket_page, is_queue_page

    if is_queue_page(page) or (event_id and not is_real_event_ticket_page(page, event_id)):
        sub_warn("Cannot add to basket — still in queue, not on ticket page")
        return False

    from .seat_map import prepare_event_page, try_pick_seat_and_basket

    apply_event_page_filters(page, config)
    qty = int(config.get("filters", {}).get("quantity", 1))
    set_quantity(page, qty)
    selected = select_first_matching_ticket(page, config, dry_run, event_id=event_id)
    if not selected:
        sub("No list rows — trying seat-map (sidebar £ / map / Add to basket)...")
        if not try_pick_seat_and_basket(page, config, dry_run):
            return False

    in_basket = dry_run or confirm_in_basket(page)
    if not in_basket:
        page.wait_for_timeout(2000)
        in_basket = confirm_in_basket(page)

    if not in_basket and not dry_run:
        sub_warn("Select clicked but basket not confirmed — no alert sent")
        return False

    from .telegram_alert import send_basket_alert

    seats = config.get("filters", {}).get("seats_together", True)
    tx = config.get("filters", {}).get("ticket_exchange", True)
    send_basket_alert(
        event_name=event_name,
        quantity=qty,
        page_url=page.url,
        dry_run=dry_run,
        seats_together=seats,
        ticket_exchange=tx,
    )
    sub_ok("Telegram basket alert sent to buyer")
    return True


def select_first_matching_ticket(
    page: Page, config: dict, dry_run: bool, *, event_id: int | None = None
) -> bool:
    """Pick best row passing filters and click Select/Buy."""
    options = scan_ticket_options(page, event_id=event_id)
    passed = _filter_options(config, options)

    if not passed:
        sub_warn("No ticket rows passed filters on screen")
        return False

    best = passed[0]
    sub_ok(f"Best match: {best.section[:50]} @ GBP {best.price or '?'}")

    clicked = _click_select_in_row(page, best, dry_run)
    if clicked and not dry_run:
        stop_before_checkout(page, dry_run=False)
    return clicked


def stop_before_checkout(page: Page, dry_run: bool) -> None:
    """Warn only when basket is confirmed — avoids false alarm on event page copy."""
    if dry_run or not confirm_in_basket(page):
        return
    try:
        body = page.locator("body").inner_text(timeout=3000).lower()
        if any(k in body for k in CHECKOUT_KEYWORDS):
            sub_warn("Basket reached — bot stops before payment (buyer pays manually)")
    except Exception:
        pass
