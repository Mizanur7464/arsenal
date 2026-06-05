"""Playwright browser helpers — persistent profile keeps login session."""

from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright

from .config_loader import ROOT
from .logger_setup import sub, sub_ok, sub_warn

OUTPUT_DIR = ROOT / "output"
PROFILE_DIR = ROOT / "data" / "browser_profile"


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR


def launch_browser(headless: bool) -> tuple[Playwright, BrowserContext, Page]:
    """Reuse saved cookies/login in data/browser_profile/."""
    sub("Starting Playwright Chromium (saved session profile)...")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        viewport={"width": 1280, "height": 900},
        locale="en-GB",
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.pages[0] if context.pages else context.new_page()
    sub_ok(f"Browser ready — profile: {PROFILE_DIR.name}/")
    return pw, context, page


def wait_after_navigation(page: Page, timeout_ms: int) -> None:
    """Queue/event pages often redirect — wait without crashing on title()."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=min(timeout_ms, 20000))
    except Exception:
        pass
    try:
        page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 25000))
    except Exception:
        pass
    page.wait_for_timeout(2000)


def safe_page_info(page: Page) -> str:
    for _ in range(4):
        try:
            title = page.title()
            return f"Title: {title[:80]} | URL: {page.url[:100]}"
        except Exception:
            page.wait_for_timeout(1500)
    try:
        return f"URL: {page.url[:120]}"
    except Exception:
        return "Page still loading (redirect)"


def goto(page: Page, url: str, timeout_ms: int, label: str = "") -> bool:
    tag = label or url[:70]
    sub(f"Opening page: [{tag}]")
    try:
        page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        sub_ok("Page loaded")
    except Exception as e:
        sub_warn(f"Navigation note: {e} (redirect is often OK)")
    wait_after_navigation(page, timeout_ms)
    sub(safe_page_info(page))
    return True


def screenshot(page: Page, name: str) -> Path:
    ensure_output_dir()
    path = OUTPUT_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    page.screenshot(path=str(path), full_page=True)
    sub(f"Screenshot saved: {path.name}")
    return path


def screenshot_on_error(page: Page, step: str) -> None:
    try:
        screenshot(page, f"error_{step}")
    except Exception:
        sub_warn("Could not save error screenshot")


def close_browser(pw: Playwright, context: BrowserContext) -> None:
    try:
        context.close()
    except Exception:
        pass
    pw.stop()
