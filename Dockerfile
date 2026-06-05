# Playwright + Chromium — required for Railway (Nixpacks alone cannot build this bot)
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent login profile (mount Railway Volume at /app/data)
RUN mkdir -p /app/data /app/output

ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true
ENV AUTO_MONITOR=true
# Railway sets RAILWAY_ENVIRONMENT automatically

CMD ["python", "run.py"]
