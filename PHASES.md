# Arsenal Bot — ৫টি Phase (বাকি কাজ)

**বর্তমান:** Phase 1–5 ✅ সম্পূর্ণ | বায়ার ডেলিভারি: `python run.py phase5`  
**লক্ষ্য:** বায়ারের Arsenal বট — টেস্ট ইভেন্ট দিয়ে স্টেবল, তারপর Chelsea আলাদা প্রজেক্ট

---

## Phase 1 — Scope ও সেটআপ (দিন ১) ✅

**লক্ষ্য:** বায়ারের চাহিদা কাগজে ঠিক করা + প্রজেক্ট রেডি

| কাজ | স্ট্যাটাস |
|-----|----------|
| বায়ারের টেস্ট গেম — নাম, URL, স্ক্রিনশট থেকে নোট | ✅ নোট + স্ক্রিনশট ID; URL Phase 2 এ বসবে |
| `config.yaml` — `test_event` + `filters` (quantity, price, section) | ✅ |
| `.env` — DRY_RUN, HEADLESS, timeout | ✅ |
| টিকেট সাইট ফ্লো ম্যাপ (লগইন → ইভেন্ট → সিট → কার্ট) | ✅ `docs/FLOW.md` |
| বায়ারকে কনফার্ম: ৫ দিন, Arsenal only, Chelsea পরে | ✅ `docs/SCOPE.md` + `docs/BUYER_UPDATE_PHASE1.txt` |

**ডেলিভারি:** `config.yaml` + `docs/FLOW.md` + `docs/SCOPE.md`  
**যাচাই:** `python run.py` বা `python run.py phase1`

---

## Phase 2 — ব্রাউজার ও পেজ অটোমেশন (দিন ২) 🟡 (লগইন OK; ইভেন্ট 3774 = Phase 3)

**লক্ষ্য:** Playwright দিয়ে সাইটে ঢোকা ও ম্যানুয়াল স্টেপগুলো কোডে

| কাজ | স্ট্যাটাস |
|-----|----------|
| `src/browser.py` — launch, timeout, screenshot on error | ✅ |
| বায়ার URL `config.yaml` এ | ✅ |
| লগইন `src/auth.py` + `.env` | ✅ কোড — আপনি credentials বসান |
| কিউ + ইভেন্ট 3774 | ✅ `src/phase2.py` |
| DRY_RUN=true — কেনা না | ✅ |

**চালান:** `python run.py phase2` — গাইড: `docs/PHASE2_SETUP.md`

---

## Phase 3 — কোর বট লজিক (দিন ৩) ✅

**লক্ষ্য:** Quantity + filters + টিকেট সিলেক্ট

| কাজ | স্ট্যাটাস |
|-----|----------|
| `src/filters.py` — রিয়েল পেজ + PASS/FAIL reason | ✅ |
| `src/tickets.py` — scan, quantity, select | ✅ |
| `src/phase3.py` — full flow + report | ✅ |
| DRY_RUN — কেনা/চেকআউট না | ✅ |

**চালান:** `python run.py phase3` — রিপোর্ট: `output/phase3_report_*.txt`

---

## Phase 4 — স্টেবিলিটি ও রিট্রাই (দিন ৪) ✅

**লক্ষ্য:** বারবার চালালে ভাঙে না — বায়ারের “stable results”

| কাজ | স্ট্যাটাস |
|-----|----------|
| `retry` + `src/retry_util.py` | ✅ |
| টাইমআউট / এরর হ্যান্ডলিং | ✅ |
| কিউ / ক্যাপচা / সেল আউট — `src/page_state.py` | ✅ |
| ৬ রান, quantity বদলে | ✅ `stability` in config |
| HEADLESS false + true | ✅ |

**চালান:** `python run.py phase4` → `output/phase4_stability_*.txt`

---

## Phase 5 — ফুল টেস্ট ও হ্যান্ডওভার (দিন ৫) ✅

**লক্ষ্য:** বায়ারকে দেওয়ার মতো Arsenal Phase 1 শেষ → Chelsea আলাদা

| কাজ | স্ট্যাটাস |
|-----|----------|
| এন্ড-টু-এন্ড টেস্ট (ইভেন্ট 3774) | ✅ `src/phase5.py` |
| `README.md` + `docs/HANDOVER.md` | ✅ |
| ভিডিও (optional) | 📄 গাইড in HANDOVER.md |
| `arsenal-bot-delivery.zip` (no .env) | ✅ phase5 তৈরি করে |
| বায়ার মেসেজ | ✅ `docs/BUYER_DELIVERY_MESSAGE.txt` |

**চালান:** `python run.py phase5`

---

## সংক্ষেপ (এক নজরে)

```
Phase 1  →  Scope + config + ফ্লো ম্যাপ
Phase 2  →  Browser + লগইন + ইভেন্ট পেজ
Phase 3  →  Filters + quantity + টিকেট সিলেক্ট
Phase 4  →  Retry + stability + বহুবার টেস্ট
Phase 5  →  ফুল টেস্ট + ডেলিভারি + Chelsea আলাদা
```

**Chelsea bot** — এই ৫ phase এর বাইরে; Arsenal শেষ হলে নতুন অর্ডার/দাম।

---

## বায়ারকে পাঠানোর ছোট আপডেট (ইংরেজি)

> I’ve broken the Arsenal bot into 5 phases: setup → browser automation → core logic (quantity/filters) → stability testing → final test & delivery. I’ll keep you updated after each phase. Chelsea will be a separate phase after Arsenal is stable.

---

## আপনার পরের স্টেপ

1. Phase 1 শুরু — স্ক্রিনশট/গেম URL পাঠান  
2. প্রতি phase শেষে বায়ারকে ২–৩ লাইন আপডেট  
3. Phase 5 এ `$700` scope অনুযায়ী হ্যান্ডওভার
