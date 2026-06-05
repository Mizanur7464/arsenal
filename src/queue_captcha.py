"""Queue-it softblock captcha + closed-queue detection."""

from playwright.sync_api import Page

from .captcha_solver import configured as captcha_configured, solve_image_base64
from .logger_setup import sub, sub_ok, sub_warn, hint


def is_queue_closed(page: Page) -> bool:
    try:
        body = page.locator("body").inner_text(timeout=5000).lower()
    except Exception:
        return False
    return any(
        x in body
        for x in (
            "queue is now closed",
            "event has ended",
            "box office event has ended",
        )
    )


def _captcha_image_locator(page: Page):
    selectors = [
        "img.captcha-code",
        'img[alt*="captcha" i]',
        'img[src*="captcha" i]',
        ".botdetect-code img",
        "canvas",
        'form img[src*="Image"]',
        "img",
    ]
    for sel in selectors:
        loc = page.locator(sel)
        try:
            n = min(loc.count(), 8)
            for i in range(n):
                img = loc.nth(i)
                if not img.is_visible(timeout=800):
                    continue
                box = img.bounding_box()
                if box and box.get("width", 0) > 80 and box.get("height", 0) > 25:
                    return img
        except Exception:
            continue
    return None


def _fill_captcha_input(page: Page, code: str) -> bool:
    selectors = [
        'input[placeholder*="picture" i]',
        'input[placeholder*="code" i]',
        'input[name*="captcha" i]',
        'input[id*="captcha" i]',
        'input[type="text"]',
    ]
    for sel in selectors:
        try:
            inp = page.locator(sel).first
            if inp.is_visible(timeout=2000):
                inp.fill(code)
                sub_ok("Captcha code entered")
                return True
        except Exception:
            continue
    return False


def _click_not_robot(page: Page) -> bool:
    for sel in (
        'button:has-text("NOT A ROBOT")',
        'button:has-text("Not a robot")',
        'input[value*="ROBOT" i]',
        'button[type="submit"]',
    ):
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                btn.click()
                page.wait_for_timeout(2500)
                sub_ok("Clicked captcha submit button")
                return True
        except Exception:
            continue
    return False


def try_solve_queue_captcha(page: Page) -> bool:
    """Solve Queue-it image captcha via 2captcha if visible."""
    if not captcha_configured():
        return False

    img = _captcha_image_locator(page)
    if not img:
        return False

    sub("Queue captcha image found — using 2captcha...")
    try:
        raw = img.screenshot(type="png")
        b64 = base64.b64encode(raw).decode("ascii")
    except Exception as e:
        sub_warn(f"Could not screenshot captcha: {e}")
        return False

    code = solve_image_base64(b64)
    if not code:
        return False

    if not _fill_captcha_input(page, code):
        sub_warn("Captcha solved but input field not found")
        return False

    _click_not_robot(page)
    page.wait_for_timeout(3000)
    return True


def handle_queue_page(page: Page) -> str:
    """
    On Queue-it page: detect closed queue or solve captcha.
    Returns: 'closed' | 'captcha_ok' | 'captcha_fail' | 'no_captcha'
    """
    if is_queue_closed(page):
        sub_warn("Queue closed / event ended on site — wait for next sale")
        hint("No tickets until Arsenal opens a new sale for this event")
        return "closed"

    if "softblock" in page.url.lower() or "queue" in page.title().lower():
        if try_solve_queue_captcha(page):
            return "captcha_ok"
        if captcha_configured() and _captcha_image_locator(page):
            return "captcha_fail"
    return "no_captcha"
