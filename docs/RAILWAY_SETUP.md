# Railway deploy — Arsenal Bot

## 1. Push code (GitHub)
Repo: `Mizanur7464/arsenal` — must include `Dockerfile`, `railway.toml`.

## 2. Railway Variables (REQUIRED)

Copy from your local `.env` into **Railway → arsenal → Variables**:

| Name | Example |
|------|---------|
| `ACCOUNT_EMAIL` | buyer@gmail.com |
| `ACCOUNT_PASSWORD` | *** |
| `TELEGRAM_BOT_TOKEN` | from BotFather |
| `TELEGRAM_CHAT_IDS` | `7820675619,7384232467` |
| `TWOCAPTCHA_API_KEY` | 2captcha key |
| `HEADLESS` | `true` |
| `DRY_RUN` | `false` |
| `TICKET_EXCHANGE` | `true` |
| `TELEGRAM_OPEN_ACCESS` | `true` |
| `PAGE_TIMEOUT_MS` | `60000` |

**Do not upload `.env` file** — Railway uses Variables only.

## 3. Redeploy
After push: **Deployments → Restart** or wait for auto-deploy.

## 4. Check logs
Success looks like:
- `Browser opened`
- `Telegram connected`
- `Monitoring ON`

## 5. UK tickets note
Railway servers may be US — Arsenal can show "Restricted access". If that happens, use UK VPS instead of Railway.

## 6. Local vs Railway
- **Local PC:** `pip install -r requirements-local.txt && playwright install chromium`
- **Railway:** uses Docker image browsers (no pip playwright)
