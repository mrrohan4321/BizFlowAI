# Backend scripts

## smoke_test.py - check a *running* server end to end

Not a pytest test. Use it after deploying (or to check local setup). It is **read-only**: it never saves or changes records,
and never prints the access token.

```bash
python backend/scripts/smoke_test.py                 # asks for Supabase URL, anon key, email, password
python backend/scripts/smoke_test.py --skip-ai       # skip assistant + extraction (no Groq needed)
BIZFLOW_API=http://localhost:8000 python backend/scripts/smoke_test.py
```

Optional env vars: `BIZFLOW_API` (default: the Render URL inside the script - change `DEFAULT_API` if the service is renamed),
`BIZFLOW_TOKEN` (skip login), `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `BIZFLOW_EMAIL`.

Steps: health (DB connected) -> summary (compares with demo known answer 45,000 / 20,000) -> overdue -> invoices -> forecast ->
assistant chat -> extraction of `sample_data/invoices/sales_INV-102_clean.png`.

Output tags: `PASS`, `WARN` (works but e.g. opening cash not set), `FAIL` (exit code 1; the message says what to check).
The first request may take ~1 minute if the Render free service was asleep.
