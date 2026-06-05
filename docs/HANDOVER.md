# Arsenal Bot — Handover (Phase 5)

## Delivered scope

- Browser automation (Playwright) for Arsenal eTicketing
- Buyer test event 3774 + queue URL configured
- Login, navigation, filters, quantity tests
- Stability runs with retry (Phase 4)
- **Not included:** Chelsea bot (new phase)

## Commands

| Command | Purpose |
|---------|---------|
| `python run.py phase1` | Verify config and files |
| `python run.py phase2` | Login + open ticket flow |
| `python run.py phase3` | Filters + quantity + scan |
| `python run.py phase4` | 6 stability runs (~15 min) |
| `python run.py phase5` | Final E2E + zip + handover report |

## Setup (buyer)

1. Python 3.10+
2. `pip install -r requirements.txt`
3. `playwright install chromium`
4. `copy .env.example .env` → add email/password
5. Edit `config.yaml` → `filters` if needed

## Safety

- `DRY_RUN=true` in `.env` — no checkout
- Never commit or share `.env`

## Proof files

- `output/phase5_handover_*.txt`
- `output/phase5_e2e_final_*.png`
- `output/phase3_report_*.txt` (if ran)
- `output/phase4_stability_*.txt` (if ran)

## Zip package

- `arsenal-bot-delivery.zip` — created by `python run.py phase5`
- Excludes: `venv/`, `.env`, `__pycache__/`

## Optional video for buyer

Record a short screen capture:

1. `python run.py phase2` — browser opens, logged in
2. Show `output/` screenshots

Windows: Win + G (Xbox Game Bar) → Record.
