# Phase 2 — আপনার করণীয় (১ মিনিট)

বায়ার URL দিয়েছে — `config.yaml` এ বসানো আছে।

## ১. `.env` এ লগইন বসান

`.env` ফাইল খুলুন (না থাকলে `.env.example` কপি করুন):

```
ACCOUNT_EMAIL=বায়ারের_ইমেইল
ACCOUNT_PASSWORD=বায়ারের_পাসওয়ার্ড
HEADLESS=false
DRY_RUN=true
PAGE_TIMEOUT_MS=60000
```

**কখনো GitHub/চ্যাটে পাসওয়ার্ড পাঠাবেন না।**

## ২. চালান

```powershell
cd "d:\ferdous project\arsenal bot"
.\venv\Scripts\activate
playwright install chromium
python run.py phase2
```

## ৩. ফলাফল

- `output/` ফোল্ডারে স্ক্রিনশট
- ইভেন্ট পেজ পর্যন্ত গেলে Phase 2 OK

2FA এলে ব্রাউজারে হাতে সম্পন্ন করে Enter চাপুন।
