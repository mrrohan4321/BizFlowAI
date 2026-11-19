# Backend tests

```bash
cd backend
TEST_DATABASE_URL=postgresql://user:pass@host:5432/db python -m pytest tests -v
```

- Needs a real Postgres (a Supabase database is fine). `TEST_DATABASE_URL` falls back to `DATABASE_URL`.
  If neither is set the whole suite is **skipped**.
- Safe for real data: `conftest.py` creates a throw-away schema `bf_test_<random>`, runs `app.db.migrate` inside it, and drops it afterwards.
  Tables are truncated before every test.
- Groq is mocked, no API key needed. JWTs are signed with a test secret (`make_token` in `conftest.py`).

## Files

| File | Covers |
|---|---|
| `conftest.py` | schema isolation, `client`, `World` (two businesses A and B + helpers), `known_answer()` demo data |
| `test_auth.py` | missing / expired / wrong-secret tokens, user without business, `X-Business-Id` rules, public health check |
| `test_invoices.py` | upload validation (type, size, unsafe filename), OCR/AI failures, extraction staging, explicit confirm, single-use + expiry, duplicates, list filters, update, delete, isolation |
| `test_payments.py` | full / partial / multiple payments, overpayment, invalid amounts, `business_id` in body rejected, isolation |
| `test_expenses_cash.py` | paid/unpaid rules, mark paid, opening cash upsert / negative / isolation |
| `test_analytics.py` | summary (known answer: receivables 45k, payables 20k), date range, overdue, monthly, isolation |
| `test_forecast.py` | 409 without opening cash, month-end rule, moving-average values, unpaid is not cash, short / empty history, parameter validation |
| `test_assistant.py` | chat with mocked Groq, missing opening cash, unsupported question, Groq outage / missing key / bad AI response, other business data never sent to Groq |
| `test_security_and_migrations.py` | every table has RLS, migrations are safe to re-run |

## Writing a new test

Use the `world` fixture (`world.biz_a`, `world.h_a` = auth headers for business A, `world.biz_b`, `world.h_b`),
helpers `add_payment`, `add_expense`, `set_opening`, `known_answer`. Always add a cross-business case: user B must get 404/empty for A's data.
