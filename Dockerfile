# Playwright + Chromium — required for Railway (Nixpacks alone cannot build this bot)
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy

WORKDIR /app

COPY requirements.txt .
# Same version as base image — reuses bundled Chromium in /ms-playwright (no playwright install)
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "from playwright.sync_api import sync_playwright; print('playwright import OK')"

COPY . .

# Persistent login profile (mount Railway Volume at /app/data)
RUN mkdir -p /app/data /app/output

ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true
ENV AUTO_MONITOR=true
# Railway sets RAILWAY_ENVIRONMENT automatically

CMD ["python", "run.py"]
