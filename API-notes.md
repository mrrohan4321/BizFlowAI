# API Contracts (shared - agree before changing)

Interactive docs: run the backend and open **http://localhost:8000/docs** (Swagger UI).

## Auth
Every endpoint except `/api/health` needs `Authorization: Bearer <Supabase access token>`.
The business is resolved on the server from the user's `business_members` row.
`X-Business-Id` is optional and only *selects* among businesses the user already belongs to.
Errors always look like `{"error": {"code": "...", "message": "...", "details": ...}}`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/invoices/extract | Upload PDF/JPG/PNG -> extraction_id, extracted_fields, warnings. **Nothing is saved.** |
| POST | /api/invoices | Save user-confirmed invoice (`"confirmed": true`, optional `extraction_id`) |
| GET | /api/invoices | List (invoice_type, status, date_from, date_to, party, limit, offset) |
| GET/PATCH/PUT/DELETE | /api/invoices/{id} | Detail / update / delete (delete blocked if payments exist) |
| POST | /api/payments | Record payment -> payment + updated invoice balance/status |
| GET | /api/payments | List payments (invoice_id, date_from, date_to) |
| GET | /api/payments/overdue | Overdue invoices (also `/api/analytics/overdue`), `?as_of=YYYY-MM-DD` |
| POST/GET | /api/expenses | Record / list expenses (`payment_status`: unpaid\|paid, `paid_date`) |
| PATCH | /api/expenses/{id} | Update, e.g. mark as paid |
| PUT/GET | /api/opening-cash | Set / list opening cash (`as_of_date` must be a month-end) |
| GET | /api/analytics/summary | sales_total, expense_total, receivables, payables, operating_surplus_estimate (`?date_from&date_to`) |
| GET | /api/analytics/monthly | labels + sales / expenses (recorded) + cash_income / cash_outflows (actual) |
| GET | /api/forecast | periods, values, method, assumptions, warnings (`?months=3&window=3`). 409 until opening cash is set |
| POST | /api/assistant/chat | `{"question": "..."}` -> answer, tool_used, data_used, insufficient_data, follow_up |

## Money rules (all computed by `ai_ml`, never by the LLM)
- Receivables = outstanding SALES invoices; payables = outstanding PURCHASE invoices; never combined.
- Overdue = due_date before today AND outstanding > 0.
- Cash history for the forecast = payments on sales invoices (income) + payments on purchase invoices and
  expenses marked **paid** (outflows). Unpaid invoices/expenses are never cash.
- Record a cost as a purchase invoice OR an expense, not both (avoids double counting).
- Forecast starts the month after `opening cash as_of_date`; payments dated after it are excluded from history.

## Invoice object
```json
{
  "id": "uuid", "invoice_number": "INV-102", "invoice_type": "sales", "party_name": "ABC Constructions",
  "invoice_date": "2026-11-10", "due_date": "2026-11-25",
  "subtotal": 10000.00, "tax_amount": 1800.00, "total_amount": 11800.00,
  "amount_paid": 0.00, "outstanding_amount": 11800.00, "status": "unpaid"
}
```
status: unpaid | partially_paid | paid
