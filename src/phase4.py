"""Phase 4 — stability: retries, error detection, multi-run report."""

import copy
import time
from dataclasses import dataclass
from datetime import datetime

from playwright.sync_api import TimeoutError as PlaywrightTimeout

from .config_loader import load_config, ROOT
from .logger_setup import banner, info, ok, warn, err
from .browser import launch_browser, close_browser, ensure_output_dir
from .session import navigate_to_event
from .page_state import detect_page_state
from .retry_util import with_retry
from .filters import apply_filters
from .tickets import scan_ticket_options, set_quantity


@dataclass
class RunResult:
    run_id: int
    headless: bool
    quantity: int
    passed: bool
    navigation: str
    page_state: str
    tickets_found: int
    tickets_passed: int
    error: str = ""
    duration_sec: float = 0.0

    def summary_line(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"Run {self.run_id:02d} | {status} | headless={self.headless} | qty={self.quantity} | "
            f"nav={self.navigation} | state={self.page_state} | "
            f"tickets={self.tickets_passed}/{self.tickets_found} | {self.duration_sec:.1f}s"
            + (f" | err={self.error[:50]}" if self.error else "")
        )


def _stability_plan(config: dict) -> list[tuple[bool, int]]:
    """Build (headless, quantity) pairs for each run."""
    stab = config.get("stability") or {}
    runs = int(stab.get("total_runs", 6))
    quantities = stab.get("quantity_tests") or [1, 1, 2, 2, 3, 3]
    headless_modes = stab.get("headless_modes")
    if headless_modes is None:
        headless_modes = [False, False, False, True, True, True]

    plan: list[tuple[bool, int]] = []
    for i in range(runs):
        h = bool(headless_modes[i % len(headless_modes)])
        q = int(quantities[i % len(quantities)])
        plan.append((h, q))
    return plan


def _run_single(
    run_id: int,
    headless: bool,
    quantity: int,
    config: dict,
    env: dict,
) -> RunResult:
    t0 = time.time()
    cfg = copy.deepcopy(config)
    cfg.setdefault("filters", {})["quantity"] = quantity

    site = config.get("site", {})
    event = config.get("test_event", {})
    retry_cfg = config.get("retry", {})
    max_attempts = int(retry_cfg.get("max_attempts", 3))
    delay = float(retry_cfg.get("delay_seconds", 2))

    base_url = site.get("base_url", "")
    queue_url = (event.get("queue_url") or "").strip()
    event_url = (event.get("url") or "").strip()
    event_id = int(event.get("event_id") or 3774)
    timeout = env["page_timeout_ms"]

    def _attempt() -> RunResult:
        pw, browser, page = launch_browser(headless)
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
            state = detect_page_state(page)
            options = scan_ticket_options(page)
            passed_filter = sum(1 for o in options if apply_filters(cfg, o.to_dict()))
            set_quantity(page, quantity)

            run_ok = nav in ("event", "site") and state.label not in ("CAPTCHA",)
            if state.label == "SOLD_OUT" and not options:
                run_ok = True  # stable detection still counts as pass

            return RunResult(
                run_id=run_id,
                headless=headless,
                quantity=quantity,
                passed=run_ok,
                navigation=nav,
                page_state=state.label,
                tickets_found=len(options),
                tickets_passed=passed_filter,
                duration_sec=time.time() - t0,
            )
        finally:
            close_browser(pw, browser)

    try:
        return with_retry(
            _attempt,
            max_attempts=max_attempts,
            delay_seconds=delay,
            label=f"run-{run_id}",
        )
    except PlaywrightTimeout as e:
        return RunResult(
            run_id=run_id,
            headless=headless,
            quantity=quantity,
            passed=False,
            navigation="failed",
            page_state="TIMEOUT",
            tickets_found=0,
            tickets_passed=0,
            error=str(e),
            duration_sec=time.time() - t0,
        )
    except Exception as e:
        return RunResult(
            run_id=run_id,
            headless=headless,
            quantity=quantity,
            passed=False,
            navigation="failed",
            page_state="ERROR",
            tickets_found=0,
            tickets_passed=0,
            error=str(e),
            duration_sec=time.time() - t0,
        )


def _write_report(results: list[RunResult]) -> None:
    ensure_output_dir()
    path = ROOT / "output" / f"phase4_stability_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    passed = sum(1 for r in results if r.passed)
    lines = [
        f"Phase 4 stability report — {datetime.now().isoformat()}",
        f"Summary: {passed}/{len(results)} runs passed",
        "",
    ]
    for r in results:
        lines.append(r.summary_line())
    lines.extend(
        [
            "",
            "--- By headless mode ---",
            f"headless=false: {sum(1 for r in results if not r.headless and r.passed)}/{sum(1 for r in results if not r.headless)} passed",
            f"headless=true:  {sum(1 for r in results if r.headless and r.passed)}/{sum(1 for r in results if r.headless)} passed",
            "",
            "--- Page states seen ---",
        ]
    )
    for label in sorted({r.page_state for r in results}):
        lines.append(f"  {label}: {sum(1 for r in results if r.page_state == label)} runs")
    path.write_text("\n".join(lines), encoding="utf-8")
    info(f"Stability report: {path.name}")


def run_phase4() -> bool:
    banner()
    info("Phase 4: Stability + retry + multi-run tests")

    config = load_config()
    env = config["_env"]

    if not env.get("account_email") or not env.get("account_password"):
        err("Set ACCOUNT_EMAIL and ACCOUNT_PASSWORD in .env")
        return False

    ok("DRY_RUN stays on — no purchases during stability runs")

    plan = _stability_plan(config)
    info(f"Running {len(plan)} stability cycles (retry from config.yaml)...")

    results: list[RunResult] = []
    for i, (headless, qty) in enumerate(plan, start=1):
        info(f"--- Stability run {i}/{len(plan)} (headless={headless}, qty={qty}) ---")
        result = _run_single(i, headless, qty, config, env)
        results.append(result)
        if result.passed:
            ok(result.summary_line())
        else:
            warn(result.summary_line())
        time.sleep(float(config.get("retry", {}).get("delay_seconds", 2)))

    _write_report(results)
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    if passed >= total * 0.6:
        ok(f"Phase 4 COMPLETE — {passed}/{total} runs stable (see output/phase4_stability_*.txt)")
        return True

    warn(f"Phase 4 PARTIAL — {passed}/{total} passed (queue/sale may be closed)")
    return passed > 0


if __name__ == "__main__":
    raise SystemExit(0 if run_phase4() else 1)
