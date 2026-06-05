"""Login for eticketing.co.uk / Arsenal (incl. SSO redirects)."""

import re

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .logger_setup import sub, sub_ok, sub_warn
from .browser import screenshot_on_error

SIGN_IN_SELECTORS = [
    'a:has-text("Sign in")',
    'a:has-text("Sign In")',
    'a:has-text("Log in")',
    'a:has-text("Login")',
    'button:has-text("Sign in")',
    '[href*="login"]',
    '[href*="signin"]',
]

EMAIL_SELECTORS = [
    'input[type="email"]',
    'input[name="email"]',
    'input[name="Email"]',
    'input[name="username"]',
    'input[id*="email" i]',
    'input[id*="username" i]',
    'input[autocomplete="email"]',
    'input[autocomplete="username"]',
]

PASSWORD_SELECTORS = [
    'input[type="password"]',
    'input[name="password"]',
    'input[name="Password"]',
]

SUBMIT_SELECTORS = [
    'button[type="submit"]',
    'input[type="submit"]',
    'button:has-text("Sign in")',
    'button:has-text("Log in")',
    'button:has-text("Continue")',
    'button:has-text("Submit")',
]

SSO_HINTS = (
    "myaccount.arsenal.com",
    "web-identity.tmtickets",
    "tmtickets.co.uk",
    "account/login",
    "/challenge",
)

COOKIE_DISMISS_SELECTORS = [
    "#onetrust-accept-btn-handler",
    'button:has-text("Accept All Cookies")',
    'button:has-text("Accept All")',
    'button:has-text("Accept all")',
    'button:has-text("I Accept")',
    'button:has-text("Allow All")',
    'button:has-text("Reject All")',  # some sites only allow proceed after interaction
    ".save-preference-btn-handler",
]


def dismiss_cookie_and_overlays(page: Page) -> None:
    """OneTrust cookie banner blocks Sign in clicks — dismiss first."""
    for sel in COOKIE_DISMISS_SELECTORS:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1500):
                btn.click(force=True)
                page.wait_for_timeout(1200)
                sub_ok("Cookie/consent popup closed")
                return
        except Exception:
            continue
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    except Exception:
        pass


def _first_visible(page: Page, selectors: list[str], timeout: int = 8000):
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.is_visible(timeout=timeout):
                return loc
        except PlaywrightTimeout:
            continue
    return None


def _fill_first(page: Page, selectors: list[str], value: str, timeout: int = 10000) -> bool:
    loc = _first_visible(page, selectors, timeout=timeout)
    if not loc:
        return False
    loc.fill(value)
    return True


def _click_first(page: Page, selectors: list[str], timeout: int = 8000) -> bool:
    loc = _first_visible(page, selectors, timeout=timeout)
    if not loc:
        return False
    loc.click()
    return True


def is_login_page(page: Page) -> bool:
    url = page.url.lower()
    return any(h in url for h in SSO_HINTS) or "login" in url or "signin" in url


def is_logged_in(page: Page) -> bool:
    """True when not on a login/SSO screen and session looks active."""
    if is_login_page(page):
        return False
    try:
        body = page.content().lower()
    except Exception:
        body = ""
    if any(x in body for x in ("sign out", "log out", "logout", "my account")):
        return True
    if _first_visible(page, SIGN_IN_SELECTORS, timeout=1500):
        return False
    return "eticketing.co.uk" in page.url.lower()


def _submit_login_form(page: Page, email: str, password: str, timeout_ms: int) -> bool:
    dismiss_cookie_and_overlays(page)
    if is_login_page(page) and _first_visible(page, SIGN_IN_SELECTORS, timeout=2000):
        sub("Clicking Sign in...")
        try:
            page.locator('button:has-text("Sign in")').first.click(force=True, timeout=8000)
        except Exception:
            _click_first(page, SIGN_IN_SELECTORS)
        page.wait_for_timeout(1500)

    sub("Filling email...")
    if not _fill_first(page, EMAIL_SELECTORS, email):
        return False
    sub_ok("Email entered")

    sub("Filling password...")
    if not _fill_first(page, PASSWORD_SELECTORS, password):
        return False
    sub_ok("Password entered")

    sub("Submitting login...")
    if not _click_first(page, SUBMIT_SELECTORS):
        page.keyboard.press("Enter")

    page.wait_for_timeout(4000)
    try:
        page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 30000))
    except PlaywrightTimeout:
        sub_warn("Page still loading after login — continuing")

    return is_logged_in(page) or not is_login_page(page)


def ensure_logged_in(
    page: Page,
    base_url: str,
    email: str,
    password: str,
    timeout_ms: int,
) -> bool:
    """Login on current page or SSO redirect; safe to call multiple times."""
    if is_logged_in(page):
        sub_ok("Session active (logged in)")
        return True

    if is_login_page(page):
        sub("SSO / login page detected — signing in...")
        if _submit_login_form(page, email, password, timeout_ms):
            sub_ok("SSO login step completed")
            return True
        screenshot_on_error(page, "sso_login")
        sub_warn("SSO login failed — complete login manually in browser (HEADLESS=false)")
        return False

    sub(f"Open site: {base_url}")
    page.goto(base_url, timeout=timeout_ms, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    if is_logged_in(page):
        sub_ok("Already logged in on eTicketing")
        return True

    dismiss_cookie_and_overlays(page)
    sub("Looking for Sign in on Arsenal site...")
    if not _click_first(page, SIGN_IN_SELECTORS):
        sub_warn("Sign in link not found — may redirect to SSO automatically")

    page.wait_for_timeout(2000)
    if _submit_login_form(page, email, password, timeout_ms):
        sub_ok("Login successful")
        return True

    screenshot_on_error(page, "login_failed")
    sub_warn("Login unclear — log in once manually; session is saved in data/browser_profile/")
    return False


def login(page: Page, base_url: str, email: str, password: str, timeout_ms: int) -> bool:
    return ensure_logged_in(page, base_url, email, password, timeout_ms)


def wait_for_event_page(page: Page, event_id: int, timeout_ms: int) -> bool:
    """Wait until real Arsenal ticket page (not Queue-it URL with event in query)."""
    from .page_state import is_real_event_ticket_page

    pattern = re.compile(
        rf"https?://www\.eticketing\.co\.uk/arsenal/EDP/Event/Index/{event_id}",
        re.I,
    )
    try:
        page.wait_for_url(pattern, timeout=timeout_ms)
        sub_ok(f"Reached real ticket page (event {event_id})")
        return True
    except PlaywrightTimeout:
        pass
    if is_real_event_ticket_page(page, event_id):
        sub_ok(f"On real ticket page (event {event_id})")
        return True
    return False
