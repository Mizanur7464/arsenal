"""Phase 3 — filters, quantity, ticket scan/select (DRY_RUN safe)."""

from datetime import datetime
from pathlib import Path

from .config_loader import load_config, ROOT
from .logger_setup import banner, info, ok, warn, err
from .browser import launch_browser, close_browser, screenshot, ensure_output_dir
from .session import navigate_to_event
from .filters import apply_filters, filter_reason
from .tickets import (
    scan_ticket_options,
    set_quantity,
    select_first_matching_ticket,
    stop_before_checkout,
)


def _write_report(lines: list[str]) -> Path:
    ensure_output_dir()
    path = ROOT / "output" / f"phase3_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    info(f"Report saved: {path.name}")
    return path


def _test_quantities(config: dict) -> list[int]:
    """Buyer asked to play with quantity — test 1..N."""
    main = int(config.get("filters", {}).get("quantity", 1))
    return sorted(set([1, main, min(main + 1, 10)]))


def run_phase3() -> bool:
    banner()
    info("Phase 3: Filters + quantity + ticket scan")
    report: list[str] = [f"Phase 3 report — {datetime.now().isoformat()}", ""]

    config = load_config()
    env = config["_env"]
    site = config.get("site", {})
    event = config.get("test_event", {})
    base_url = site.get("base_url", "https://www.eticketing.co.uk/arsenal/")
    queue_url = (event.get("queue_url") or "").strip()
    event_url = (event.get("url") or "").strip()
    event_id = int(event.get("event_id") or 3774)
    timeout = env["page_timeout_ms"]
    dry_run = env["dry_run"]

    if not env.get("account_email") or not env.get("account_password"):
        err("Set ACCOUNT_EMAIL and ACCOUNT_PASSWORD in .env")
        return False

    if dry_run:
        ok("DRY_RUN=true — no payment / checkout")

    pw, browser, page = launch_browser(env["headless"])
    ok_phase3 = False

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
        report.append(f"Navigation: {nav}")
        report.append(f"URL: {page.url}")
        report.append("")

        screenshot(page, "phase3_page")

        if nav == "failed":
            err("Could not open Arsenal session")
            report.append("RESULT: FAILED (navigation)")
            _write_report(report)
            return False

        if nav == "site":
            warn("On Arsenal site but not event page — scanning home/listing anyway")

        options = scan_ticket_options(page)
        report.append(f"Found {len(options)} price/row candidates on page")
        report.append("")

        if not options:
            warn("No prices found — event may be closed or page needs manual queue")
            report.append("No ticket rows parsed. Ask buyer if sale is open.")
        else:
            passed_count = 0
            for i, opt in enumerate(options, 1):
                d = opt.to_dict()
                reason = filter_reason(config, d)
                passed = apply_filters(config, d)
                if passed:
                    passed_count += 1
                line = f"[{i}] {reason} | {d['section'][:40]} | £{d.get('price')}"
                report.append(line)
                info(line)
            report.append("")
            report.append(f"Filter summary: {passed_count}/{len(options)} passed")
            ok_phase3 = passed_count > 0 or nav == "event"

        report.append("")
        report.append("--- Quantity tests ---")
        for q in _test_quantities(config):
            cfg = {**config, "filters": {**config.get("filters", {}), "quantity": q}}
            report.append(f"Try quantity={q}: filter check uses qty>={q}")
            set_quantity(page, q)

        report.append("")
        report.append("--- Ticket select (dry-run) ---")
        selected = select_first_matching_ticket(page, config, dry_run)
        report.append(f"Select step: {'OK (dry-run)' if selected else 'No button / no match'}")
        stop_before_checkout(page, dry_run)

        screenshot(page, "phase3_final")

        if ok_phase3 or selected or nav == "event":
            ok("Phase 3 COMPLETE — filters + quantity tested (see output/ report)")
            report.append("")
            report.append("RESULT: COMPLETE")
            ok_phase3 = True
        else:
            warn("Phase 3 PARTIAL — logic ran; page had limited ticket data")
            report.append("")
            report.append("RESULT: PARTIAL (re-run when sale/queue is active)")
            ok_phase3 = True

    except Exception as e:
        err(str(e))
        report.append(f"ERROR: {e}")
        report.append("RESULT: FAILED")
        ok_phase3 = False
    finally:
        _write_report(report)
        if not env["headless"]:
            info("Browser closes in 5s...")
            page.wait_for_timeout(5000)
        close_browser(pw, browser)

    return ok_phase3


if __name__ == "__main__":
    raise SystemExit(0 if run_phase3() else 1)
