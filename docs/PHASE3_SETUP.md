# Phase 3 — চালানো

```powershell
cd "d:\ferdous project\arsenal bot"
.\venv\Scripts\activate
python run.py phase3
```

## কী করবে

1. লগইন + ইভেন্ট/কিউ পেজ
2. পেজ থেকে দাম/সেকশন স্ক্যান
3. `config.yaml` → `filters` অনুযায়ী PASS/FAIL
4. Quantity 1, main, main+1 টেস্ট
5. DRY_RUN — Select ক্লিক সিমুলেট, পেমেন্ট না

## ফলাফল

- `output/phase3_report_*.txt` — বিস্তারিত লগ
- `output/phase3_*.png` — স্ক্রিনশট

## Filters বদলাতে

`config.yaml`:

```yaml
filters:
  quantity: 2
  max_price: 80
  sections: ["North Bank"]   # খালি = যেকোনো
```
