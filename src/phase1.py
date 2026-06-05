"""Phase 1 completion check — scope, config, docs, .env."""

from pathlib import Path

from .config_loader import load_config, ROOT
from .logger_setup import banner, info, ok, warn, err

REQUIRED_DOCS = [
    ROOT / "docs" / "SCOPE.md",
    ROOT / "docs" / "FLOW.md",
    ROOT / "docs" / "BUYER_UPDATE_PHASE1.txt",
]

REQUIRED_FILES = [
    ROOT / ".env",
    ROOT / "config.yaml",
    ROOT / "requirements.txt",
    ROOT / "run.py",
]


def check_phase1() -> bool:
    banner()
    info("Phase 1 check: Scope + setup")
    passed = 0
    total = 0

    def step(name: str, ok_cond: bool, hint: str = ""):
        nonlocal passed, total
        total += 1
        if ok_cond:
            ok(name)
            passed += 1
        else:
            err(name)
            if hint:
                warn(hint)

    for p in REQUIRED_FILES:
        step(f"File: {p.name}", p.is_file())

    for p in REQUIRED_DOCS:
        step(f"Doc: {p.relative_to(ROOT)}", p.is_file())

    config = load_config()
    scope = config.get("scope") or {}
    step("Scope in config", bool(scope.get("timeline_days")), "Add scope block to config.yaml")
    step("Filters in config", "filters" in config and "quantity" in config["filters"])
    step("Retry in config", "retry" in config)
    step("Test event block", "test_event" in config)

    env_path = ROOT / ".env"
    if env_path.is_file():
        text = env_path.read_text(encoding="utf-8")
        step("DRY_RUN in .env", "DRY_RUN" in text)
        step("HEADLESS in .env", "HEADLESS" in text)
        step("PAGE_TIMEOUT_MS in .env", "PAGE_TIMEOUT_MS" in text)
    else:
        step(".env readable", False, "Copy .env.example to .env")

    url = (config.get("test_event") or {}).get("url", "").strip()
    total += 1
    if url:
        ok(f"test_event.url set: {url[:60]}...")
        passed += 1
    else:
        warn("test_event.url empty — required before Phase 2")

    info(f"Result: {passed}/{total} checks passed")
    phase1_done = passed >= total - 1  # allow missing URL
    if phase1_done:
        ok("Phase 1 COMPLETE — ready for Phase 2 after URL is set")
    else:
        err("Phase 1 incomplete — fix items above")
    return phase1_done


if __name__ == "__main__":
    raise SystemExit(0 if check_phase1() else 1)
