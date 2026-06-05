"""Phase 2 — browser open, login, reach buyer ticket page."""

from .config_loader import load_config
from .logger_setup import banner, info, ok, warn, err
from .browser import launch_browser, screenshot, close_browser, ensure_output_dir
from .session import navigate_to_event
from .auth import wait_for_event_page


def _credentials_ok(env: dict) -> bool:
    return bool(env.get("account_email") and env.get("account_password"))


def run_phase2() -> bool:
    banner()
    info("Phase 2: Browser + login + ticket page")
    ensure_output_dir()

    config = load_config()
    env = config["_env"]
    site = config.get("site", {})
    event = config.get("test_event", {})
    base_url = site.get("base_url", "https://www.eticketing.co.uk/arsenal/")
    queue_url = (event.get("queue_url") or "").strip()
    event_url = (event.get("url") or "").strip()
    event_id = int(event.get("event_id") or 3774)
    timeout = env["page_timeout_ms"]

    if not event_url:
        err("test_event.url missing in config.yaml")
        return False

    if not _credentials_ok(env):
        err("Add ACCOUNT_EMAIL and ACCOUNT_PASSWORD in .env")
        return False

    if env["dry_run"]:
        ok("DRY_RUN=true — will not purchase tickets")

    pw, browser, page = launch_browser(env["headless"])
    success = False

    try:
        nav = navigate_to_event(
            page,
            base_url=base_url,
            queue_url=queue_url,
            event_url=event_url,
            event_id=event_id,
            email=env["account_email"],
            password=env["account_password"],
            timeout_ms=timeout,
        )
        screenshot(page, "phase2_final")
        on_event = wait_for_event_page(page, event_id, timeout_ms=5000) or nav == "event"

        if on_event:
            ok(f"Phase 2 COMPLETE — event page: {page.url[:95]}...")
            success = True
        elif nav == "site":
            warn("Phase 2 PARTIAL — logged in on Arsenal site, event page not loaded")
            success = True
        else:
            err("Phase 2 failed — see output/ screenshots")
    except Exception as e:
        err(str(e))
        success = False
    finally:
        if not env["headless"]:
            page.wait_for_timeout(5000)
        close_browser(pw, browser)

    return success


if __name__ == "__main__":
    raise SystemExit(0 if run_phase2() else 1)
