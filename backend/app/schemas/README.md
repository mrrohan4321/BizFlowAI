# 📝 schemas/

Pydantic request models. Almost all use `extra="forbid"`: any unknown field, including a client-sent
`business_id`, is rejected with `422 invalid_request`. Strings are stripped.

| File | Models |
|---|---|
| `invoices.py` | `InvoiceConfirm` (needs `confirmed: true`), `InvoiceUpdate` |
| `finance.py` | `PaymentCreate`, `ExpenseCreate`, `ExpenseUpdate`, `OpeningCashSet` |
| `assistant.py` | `AssistantQuestion` (1 to 500 characters) |

Important validation rules: money has at most 14 digits and 2 decimals; payment amount > 0; expense `paid` needs `paid_date`
and `unpaid` must not have one; opening cash `as_of_date` must be a month end (the amount may be negative).
Responses are plain dicts built in services (no response models), so the response shapes are documented in
`backend/README.md` (section 5, Endpoints).
