# Phase 4 — Stability tests

## Run

```powershell
python run.py phase4
```

**Time:** ~10–15 minutes (6 browser runs with retries).

## What it does

- 6 runs with different **quantity** (1, 2, 3)
- **headless=false** for runs 1–3, **headless=true** for runs 4–6
- Each run retries up to `retry.max_attempts` on failure
- Detects **QUEUE**, **CAPTCHA**, **SOLD_OUT**, **EVENT**, **TIMEOUT**
- Writes `output/phase4_stability_*.txt`

## Tune in config.yaml

```yaml
retry:
  max_attempts: 3
  delay_seconds: 2

stability:
  total_runs: 6
  headless_modes: [false, false, false, true, true, true]
  quantity_tests: [1, 2, 1, 2, 3, 1]
```

## Pass criteria

- 60%+ runs pass → Phase 4 COMPLETE
- Lower pass rate → often queue closed or no sale — still logged in report
