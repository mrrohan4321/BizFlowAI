# 🧩 services/

The real work. Every query filters by `business_id`. Multi-step writes use one transaction
(`get_connection()`); single statements use `get_cursor()`.

| File | What it does | Uses from ai_ml |
|---|---|---|
| `invoices.py` | extract + stage, confirm (explicit save), list/get/update/delete | `extract_invoice`, `validate_invoice`, `InvoiceFields` |
| `uploads.py` | safe file storage: allowed types, magic bytes, size limit, server-made file names, path guard | none |
| `payments.py` | record/list payments, `invoice_balance()` (amount paid, outstanding, status) | `outstanding`, `invoice_status`, `money` |
| `expenses.py` | create/list/update expenses (mark paid) | none |
| `cash.py` | opening cash balance upsert/list | none |
| `analytics.py` | load records, cash history, summary, overdue, monthly, forecast | `calculate_business_summary`, `get_overdue_invoices_tool`, `get_monthly_performance`, `get_forecast` |
| `assistant.py` | load this business's data and call the assistant, map failures to safe errors | `assistant.answer_finance_question` |

Things to remember:

- `invoice_balance()` is the single place that attaches `amount_paid / outstanding_amount / status` to an invoice.
- Locking: `FOR UPDATE` on invoices and extractions prevents double payment and double confirm.
- Errors are raised as `AppError`; never return exception text to the client.
- `ai_ml.assistant` is imported lazily inside `assistant.chat`, so the app starts even without the Groq SDK configured.
