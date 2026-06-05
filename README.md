# Arsenal Bot — Delivery Package

Python browser bot for **Arsenal eTicketing** (buyer test event 3774).  
**Chelsea bot** = separate project / price.

All 5 phases implemented. Start with **Phase 1 check**, finish with **Phase 5 handover**.

---

## Quick start (Windows)

```powershell
cd "d:\ferdous project\arsenal bot"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
```

Edit **`.env`** — add `ACCOUNT_EMAIL` and `ACCOUNT_PASSWORD`.  
Edit **`config.yaml`** — `filters` (quantity, max_price, sections).

---

## Run (one command)

```powershell
python run.py
```

Does everything: ticket scan + Telegram (`/start`, `/status`, `/start_on`, `/stop`).  
Stays open after scan — **Ctrl+C** to stop.

---

## Telegram alerts

Add to `.env`:

```
TELEGRAM_BOT_TOKEN=from_botfather
TELEGRAM_CHAT_ID=your_chat_id
```

When a ticket matches and basket step runs, you get a message like:  
`Ticket found (2): Added to Basket`

**Commands in Telegram:**

| Command | Action |
|---------|--------|
| `/start` | Welcome message |
| `/status` | Monitoring on/off, event, last run |
| `/start_on` | Start searching (loop) |
| `/stop` | Stop searching |

---

## Safety

- **`DRY_RUN=true`** in `.env` — no payment (default)
- **`HEADLESS=false`** — see browser while testing
- Never share **`.env`** or commit it to Git

---

## Project layout

```
arsenal bot/
  run.py              # Main entry
  config.yaml         # Event URLs, filters, retry, stability
  .env.example        # Template (copy to .env)
  src/
    phase1.py … phase5.py
    session.py        # Login + navigation
    tickets.py        # Scan, quantity, select
    page_state.py     # Queue / captcha / sold out
  docs/
    HANDOVER.md       # Buyer handover guide
    BUYER_DELIVERY_MESSAGE.txt
  output/             # Screenshots + reports (after runs)
```

---

## Deliver to buyer

1. Run: `python run.py phase5`
2. Send:
   - `arsenal-bot-delivery.zip`
   - `output/phase5_e2e_final_*.png`
   - `output/phase5_handover_*.txt`
   - Copy text from `docs/BUYER_DELIVERY_MESSAGE.txt`

---

## Docs

| File | Purpose |
|------|---------|
| `PHASES.md` | All 5 phases checklist |
| `docs/SCOPE.md` | $700 scope, 5 days, Chelsea later |
| `docs/FLOW.md` | Ticket site flow |
| `docs/HANDOVER.md` | Full handover |

---

## Note

Respect eTicketing terms of service. Use dry-run until buyer confirms live testing.
