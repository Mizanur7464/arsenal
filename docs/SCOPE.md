# Project scope (Phase 1 — agreed with buyer)

## What we are building

| Item | Detail |
|------|--------|
| Product | **Arsenal bot** — Python browser automation |
| Not included | Telegram bot (unless buyer asks later) |
| Phase 2 later | **Chelsea bot** — new scope and price |
| Budget | **$700** (finalize exact scope before full build) |
| Timeline | **5 days** — design + test on buyer fixture |

## Buyer messages (summary)

1. **Timeline:** 5 days OK if bot is fully designed within deadline so Chelsea can start without delay.
2. **Testing:** Seller picks any event for dev tests; buyer provided **one specific game** (screenshot) for real fixture test — others closed or hard to get.
3. **Parameters:** Quantity and filters adjustable during testing.
4. **Price:** Agree scope and price before start; Arsenal + testing + stability in current order; Chelsea separate.

## Deliverables (this order)

1. Phase 1 — Scope, config, flow map (this document set)
2. Phase 2 — Browser opens buyer event page
3. Phase 3 — Quantity + filters + ticket selection logic
4. Phase 4 — Retry and stability
5. Phase 5 — End-to-end test + handover

## Out of scope (unless buyer pays extra)

- Chelsea FC bot
- Telegram control panel
- Hosting / VPS setup (unless agreed)
- Bypassing captcha or queue systems against site rules

## Your action before Phase 2

Paste the **exact ticket page URL** from the buyer screenshot into `config.yaml` → `test_event.url`.
