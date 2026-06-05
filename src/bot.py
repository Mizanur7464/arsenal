"""Main flow — dry run by default (safe testing)."""

from .config_loader import load_config
from .logger_setup import banner, info, ok, warn
from .filters import apply_filters
from .browser import launch_browser, goto, close_browser


def run_test_flow() -> None:
    banner()
    config = load_config()
    env = config["_env"]
    event = config.get("test_event", {})
    filters = config.get("filters", {})

    info(f"Event: {event.get('name') or '(not set yet)'}")
    info(f"Quantity: {filters.get('quantity')} | Dry run: {env['dry_run']}")

    # Example: pretend we found a ticket (replace with real logic later)
    sample = {"price": 45, "section": "Test Block", "qty_available": 2}
    if apply_filters(config, sample):
        ok("Filter check passed on sample data")
    else:
        warn("Filter check failed on sample data")

    if env["dry_run"]:
        ok("DRY_RUN=true — no purchase. Only testing setup + filters.")
        if event.get("url"):
            info("Optional: open browser to inspect the ticket page...")
            pw, browser, page = launch_browser(env["headless"])
            try:
                goto(page, event["url"], env["page_timeout_ms"], label="event")
                input("\nPress Enter to close browser...")
            finally:
                close_browser(pw, browser)
        return

    warn("Real run not implemented yet — finish config + buyer selectors first.")


if __name__ == "__main__":
    run_test_flow()
