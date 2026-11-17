# API Contracts (shared - agree before changing)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/invoices/extract | Upload file -> extraction_id, extracted_fields, warnings (not saved) |
| POST | /api/invoices | Save confirmed invoice -> saved invoice + balance |
| GET | /api/invoices | List invoices (type/status/date filters) |
| GET | /api/analytics/summary | sales_total, expense_total, receivables, payables, operating_surplus_estimate |
| GET | /api/analytics/monthly | monthly labels + sales/expense arrays |
| POST | /api/payments | Record payment -> payment + updated invoice balance/status |
| GET | /api/payments/overdue | overdue invoices, days overdue, outstanding |
| GET | /api/forecast | periods, values, method, assumptions |
| POST | /api/assistant/chat | answer, data_used, follow_up (optional) |

## Invoice object
```json
{
  "id": "uuid",
  "invoice_number": "INV-102",
  "invoice_type": "sales",
  "party_name": "ABC Constructions",
  "invoice_date": "2026-11-10",
  "due_date": "2026-11-25",
  "subtotal": 10000.00,
  "tax_amount": 1800.00,
  "total_amount": 11800.00,
  "amount_paid": 0.00,
  "outstanding_amount": 11800.00,
  "status": "unpaid"
}
```
status: unpaid | partially_paid | paid
