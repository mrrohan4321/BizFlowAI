# BizFlowAI — Complete Backend Implementation Handoff

## YOUR ROLE

You are the lead backend engineer for **BizFlowAI**, a small-business financial management application.

Your task is to inspect the existing repository and implement the complete backend required to integrate the existing AI/ML module with the application.

You are expected to work directly in the project workspace, create or modify the necessary backend files, connect the database, implement APIs, and run tests.

Do not merely explain how to implement the backend. Actually implement it.

Work systematically and complete as much of the implementation as possible without requiring unnecessary clarification.

---

# 1. PROJECT OVERVIEW

BizFlowAI is an AI-powered financial management application designed for small businesses.

Its main capabilities are:

1. Invoice upload and OCR-based data extraction.
2. Invoice validation and human review.
3. Customer receivables management.
4. Supplier payables management.
5. Payment tracking.
6. Expense tracking.
7. Overdue invoice detection.
8. Monthly financial performance analysis.
9. Cash-flow forecasting.
10. Natural-language financial assistance.

The project already contains an independently developed Python AI/ML module.

**Your primary responsibility is to build the backend around that existing module.**

Do not unnecessarily rewrite the AI/ML implementation.

---

# 2. FIRST TASK: INSPECT THE EXISTING REPOSITORY

Before writing code:

1. Inspect the complete project directory structure.
2. Identify the existing backend framework.
3. Identify the frontend framework and how it communicates with the backend.
4. Inspect existing database models and migrations.
5. Inspect authentication and authorization.
6. Inspect existing API routes, serializers, schemas and services.
7. Inspect environment configuration and dependency files.
8. Inspect the existing AI/ML module and its actual public function signatures.
9. Identify existing functionality that can be reused.
10. Identify incomplete functionality and integration gaps.

Do not assume that the project uses Django, FastAPI, Flask or any other framework. Discover the actual framework from the repository.

Do not create a second backend framework alongside the existing one.

Do not overwrite working files unnecessarily.

Preserve existing conventions and architecture.

If a required feature already exists, extend it instead of duplicating it.

---

# 3. AI/ML MODULE — EXISTING IMPLEMENTATION

The AI/ML module is located at:

`ai_ml/`

It already contains these modules:

- `config.py`
- `schemas.py`
- `ocr.py`
- `invoice_extraction.py`
- `validation.py`
- `finance_metrics.py`
- `forecasting.py`
- `assistant_tools.py`
- `assistant.py`

It also contains automated tests under:

`ai_ml/tests/`

The AI/ML module is responsible for:

- OCR.
- Invoice field extraction.
- Invoice validation.
- Financial calculations.
- Overdue invoice detection.
- Monthly performance analysis.
- Cash-flow forecasting.
- Natural-language financial assistance.

The backend is responsible for:

- Authentication.
- Database operations.
- Business data retrieval.
- Business-level authorization.
- File uploads and storage.
- API endpoints.
- Invoice persistence.
- Payment and expense persistence.
- Frontend communication.

**Important: Python AI/ML functions are the source of truth for financial calculations.**

Do not duplicate financial arithmetic in API views, serializers, frontend code or LLM prompts.

---

# 4. INVOICE MANAGEMENT

Implement a complete invoice management workflow.

The backend should support:

- Uploading PDF invoices.
- Uploading JPG/JPEG invoices.
- Uploading PNG invoices.
- Validating uploaded file types and sizes.
- Safely storing uploaded files.
- Calling the existing AI/ML invoice extraction function.
- Returning extracted fields and validation issues.
- Allowing users to review and edit extracted fields.
- Saving invoices only after explicit user confirmation.
- Retrieving invoice details.
- Listing invoices.
- Filtering invoices by type, status, date and customer/supplier.
- Updating invoice information.
- Tracking invoice payment status.

## AI/ML integration

Use the existing function:

`ai_ml.invoice_extraction.extract_invoice(file_path)`

It returns an `InvoiceExtractionResult` containing:

- `fields`
- `issues`
- `needs_review`
- `source_file`
- `raw_text_preview`

The extracted invoice fields are defined by the existing `InvoiceFields` Pydantic model.

Fields include:

- `invoice_number`
- `invoice_type`
- `party_name`
- `invoice_date`
- `due_date`
- `subtotal`
- `tax_amount`
- `cgst`
- `sgst`
- `igst`
- `total_amount`
- `gstin`

Monetary fields use Decimal values.

Dates use Python date values.

The extraction function does not automatically save invoices.

## Critical workflow

Implement the following sequence:

1. User uploads an invoice.
2. Backend validates the uploaded file.
3. Backend temporarily stores or safely references the file.
4. Backend calls `extract_invoice()`.
5. Backend returns extracted fields and validation issues.
6. Frontend displays the extracted information.
7. User reviews and corrects the information.
8. User explicitly confirms the invoice.
9. Backend validates the confirmed information.
10. Backend saves the invoice in the database.

Never automatically persist an AI-extracted invoice without user confirmation.

An invoice with missing fields or validation warnings must remain reviewable.

Do not treat the presence of extracted fields as proof that an invoice is legally or financially valid.

---

# 5. DATABASE DESIGN

Inspect the existing database models before creating new ones.

Reuse existing models wherever possible.

Ensure the database can represent the following concepts.

## Business

A business or organization that owns financial records.

Suggested information:

- Business identifier.
- Business name.
- Owner or authorized users.
- Contact information.
- Created and updated timestamps.

## Invoice

Suggested information:

- Invoice identifier.
- Business relationship.
- Invoice number.
- Invoice type: sales or purchase.
- Customer or supplier name.
- Invoice date.
- Due date.
- Subtotal.
- Tax amount.
- CGST.
- SGST.
- IGST.
- Total amount.
- Notes.
- File reference.
- Validation/review status.
- Created and updated timestamps.

## Payment

Suggested information:

- Payment identifier.
- Business relationship.
- Related invoice.
- Payment amount.
- Payment date.
- Payment method.
- Reference number.
- Notes.

Support partial payments and multiple payments against one invoice if compatible with the existing architecture.

## Expense

Suggested information:

- Expense identifier.
- Business relationship.
- Description.
- Category.
- Amount.
- Expense date.
- Payment status, if applicable.
- Notes.

## Opening cash balance

The forecasting module needs an actual opening cash balance.

Inspect whether the existing application already stores cash balances or financial account balances.

If not, implement an appropriate way to maintain an opening cash balance, with a clear business relationship and effective date.

Do not silently assume that a missing opening cash balance is zero.

Do not confuse unpaid invoice totals with actual cash received.

## Data integrity

Use appropriate:

- Foreign keys.
- Database constraints.
- Decimal fields for money.
- Date fields.
- Indexes.
- Unique constraints where appropriate.
- Transactions for operations involving multiple database writes.

Prevent users from accessing records belonging to other businesses.

---

# 6. FINANCIAL CALCULATIONS

Use the existing AI/ML financial calculation functions.

Inspect their actual signatures and required input formats before integration.

Relevant functions include:

- `calculate_business_summary()`
- `get_overdue_invoices()`
- `money()`

They are implemented in:

`ai_ml/finance_metrics.py`

The backend must retrieve the appropriate business records and pass them to these functions.

Do not independently recalculate receivables, payables or overdue balances in API endpoints.

## Receivables

Receivables represent outstanding money customers owe the business.

Use sales invoices and their associated payments.

Outstanding balance:

Invoice total minus payments received.

Do not count purchase invoices as customer receivables.

## Payables

Payables represent outstanding money the business owes suppliers.

Use purchase invoices and their associated payments.

Outstanding balance:

Invoice total minus payments made.

Do not count sales invoices as supplier payables.

## Overdue invoices

Use:

`get_overdue_invoices(invoices, payments, business_id, today)`

An invoice is overdue when:

- Its due date is earlier than the supplied date.
- Its outstanding balance is greater than zero.

The returned records include:

- `invoice_id`
- `invoice_number`
- `party_name`
- `outstanding`
- `days_overdue`

Use the existing implementation rather than writing a second overdue calculation.

---

# 7. CASH-FLOW FORECASTING

Use:

`ai_ml.forecasting.get_forecast()`

Its documented function signature is:

`get_forecast(monthly_history, opening_cash=0, forecast_months=3, window=3)`

Inspect the actual implementation before integrating it.

Expected historical input resembles:

```python
[
    {
        "month": "2026-08",
        "income": 50000,
        "outflows": 30000
    },
    {
        "month": "2026-09",
        "income": 60000,
        "outflows": 35000
    },
    {
        "month": "2026-10",
        "income": 55000,
        "outflows": 32000
    }
]
```

Important data definitions:

- `income` means actual cash received.
- `outflows` means actual cash paid out.
- `month` identifies the historical month.
- `opening_cash` is the cash balance at the end of the last historical month.

The default forecasting approach uses a moving average of recent historical months.

The backend must:

1. Retrieve actual payments received.
2. Group actual income by month.
3. Retrieve actual expenses and cash outflows.
4. Group actual outflows by month.
5. Scope all records to the authenticated business.
6. Retrieve the actual opening cash balance.
7. Call the existing forecasting function.
8. Return the resulting forecast and assumptions.

Do not count unpaid invoices as received income.

Do not count unpaid bills as cash already paid.

Do not fabricate historical values.

Do not silently present a zero opening balance as an actual business cash position.

When insufficient history exists, communicate that limitation clearly.

The forecasting method is an explainable baseline, not a guarantee of future cash balances.

## Important cash-outflow rules

Use actual recorded cash transactions when constructing historical outflows.

Do not automatically equate all recorded expenses with cash payments.

- Exclude unpaid expenses and unpaid bills from actual cash outflows.
- Include payments only when they represent money actually paid.
- Avoid double-counting payments already represented in expense records.
- Do not count the same transaction through both an expense record and a payment record.
- Preserve a clear distinction between expense recognition and cash movement.

---

# 8. FINANCIAL ASSISTANT

Integrate the existing:

`ai_ml.assistant.answer_finance_question()`

Inspect `ai_ml/assistant.py` for its exact current signature, optional arguments and response behaviour.

The assistant supports questions such as:

- How much money do my customers owe me?
- What are my outstanding payables?
- Which invoices are overdue?
- How did my business perform this month?
- What is my expected cash flow?

The assistant uses five approved deterministic Python tools defined in:

`ai_ml/assistant_tools.py`

| Tool | Purpose |
|---|---|
| `get_receivables_summary` | Customer receivables |
| `get_payables_summary` | Supplier payables |
| `get_overdue_invoices` | Overdue invoices |
| `get_monthly_performance` | Monthly financial performance |
| `get_cash_forecast` | Cash-flow forecasting |

The architecture works as follows:

1. LLM selects an approved tool.
2. Python executes the selected function.
3. Python performs the financial calculations.
4. LLM explains the calculated result.

The LLM must not perform financial arithmetic or generate SQL.

The backend must retrieve and provide the relevant business data before calling the assistant.

The assistant response uses the existing `AssistantResponse` Pydantic schema.

Its fields include:

- `question`
- `answer`
- `tool_used`
- `data`
- `insufficient_data`

Serialize the response using the existing model's serialization facilities, for example:

`result.model_dump()`

Handle Groq service failures and insufficient-data responses gracefully.

Do not expose API keys or internal exception details to frontend users.

## Important existing implementation limitation

The current `answer_finance_question()` signature accepts an `expenses` argument, but the five existing registered assistant tools do not directly consume that argument.

Do not assume that passing expenses automatically enables expense-related assistant analytics.

Preserve the existing tool behaviour and implement additional functionality only if explicitly required.

If expense-related assistant questions are added, implement them through an explicitly approved deterministic Python tool and appropriate tests. Do not let the LLM calculate expense totals itself.

---

# 9. API ENDPOINTS

Implement REST API endpoints using the existing backend framework and conventions.

The following endpoint names are suggested. Adapt them to the existing API architecture rather than creating conflicting routes.

| Suggested endpoint | Responsibility |
|---|---|
| `POST /api/invoices/extract` | Upload and extract invoice information |
| `POST /api/invoices` | Save user-confirmed invoice |
| `GET /api/invoices` | List invoices |
| `GET /api/invoices/{id}` | Retrieve invoice details |
| `PUT/PATCH /api/invoices/{id}` | Update invoice |
| `DELETE /api/invoices/{id}` | Delete invoice if supported |
| `POST /api/payments` | Record payment |
| `GET /api/payments` | List payments |
| `POST /api/expenses` | Record expense |
| `GET /api/expenses` | List expenses |
| `GET /api/analytics/summary` | Business financial summary |
| `GET /api/analytics/overdue` | Overdue invoice information |
| `GET /api/analytics/monthly` | Monthly performance |
| `GET /api/forecast` | Cash-flow forecast |
| `POST /api/assistant/chat` | Financial assistant |

For every endpoint:

- Validate input.
- Authenticate the user.
- Authorize access to the requested business.
- Validate database relationships.
- Return consistent response structures.
- Handle errors appropriately.
- Avoid exposing internal implementation details.

Use appropriate HTTP status codes.

---

# 10. AUTHENTICATION AND BUSINESS ISOLATION

This is a critical security requirement.

The backend must ensure that financial records are isolated by business.

The authenticated user must only access businesses they are authorized to use.

**Never trust a business identifier supplied directly by the frontend as proof of authorization.**

Instead:

1. Authenticate the user.
2. Determine their authorized business or businesses.
3. Retrieve records belonging to that business.
4. Pass only authorized records to the AI/ML functions.
5. Verify ownership before every read, update or delete operation.

The backend must enforce isolation for:

- Invoices.
- Payments.
- Expenses.
- Financial summaries.
- Forecasting data.
- Assistant requests.
- Uploaded files.

Some AI/ML functions perform additional business-level filtering. This is useful defensive validation but does not replace backend authorization.

Never send records from unrelated businesses to Groq.

---

# 11. SECURITY AND FILE HANDLING

Implement appropriate protection for:

- File upload size.
- File extensions.
- File content validation.
- Unsafe filenames.
- Path traversal.
- Temporary file cleanup.
- Authentication.
- Authorization.
- Request validation.
- Sensitive environment variables.
- Error messages.
- Database access.

Never expose the Groq API key to the frontend.

Never commit `.env` files or API keys.

The AI/ML configuration is located in `ai_ml/config.py`.

It uses environment variables including:

- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GROQ_TIMEOUT_SECONDS`
- `MIN_TEXT_CHARS_PER_PAGE`
- `AMOUNT_TOLERANCE`

Preserve the existing configuration approach.

Ensure environment variables are loaded before importing modules that depend on them.

Invoice extraction sends invoice text to Groq. Account for this third-party processing in the application's privacy and data-handling approach.

---

# 12. ERROR HANDLING

Implement consistent error handling for:

- Invalid requests.
- Unauthenticated users.
- Unauthorized business access.
- Missing database records.
- Invalid invoice data.
- Unsupported file types.
- Oversized files.
- OCR failures.
- Groq API failures.
- Invalid AI extraction results.
- Missing historical financial records.
- Invalid opening cash balances.
- Database failures.

Distinguish between:

1. File/OCR processing failures.
2. AI extraction failures.
3. Invoice validation warnings.
4. Database failures.
5. Financial data insufficiency.
6. External AI service unavailability.

Do not silently convert failures into apparently successful financial results.

Do not expose raw stack traces to users.

Log useful diagnostic information without logging API secrets or unnecessary sensitive financial information.

---

# 13. DEPENDENCIES AND ENVIRONMENT

Inspect existing dependency files first.

Do not blindly replace the project's dependencies.

Ensure the backend environment includes the dependencies required by the existing AI/ML module.

Respect the versions and compatibility of the existing Python environment.

Do not create conflicting virtual environments unnecessarily.

Provide an updated `.env.example` containing placeholder values only.

Do not put actual API keys in `.env.example`.

Document setup and startup commands according to the actual framework discovered in the repository.

---

# 14. TESTING REQUIREMENTS

Inspect existing tests before adding new ones.

Do not delete working tests merely to make the suite pass.

Write backend tests for:

### Authentication and security

- Unauthenticated requests.
- Unauthorized business access.
- Cross-business record isolation.
- Ownership checks on update and delete.

### Invoice management

- Valid uploads.
- Unsupported formats.
- Oversized uploads.
- Successful extraction.
- Extraction errors.
- Validation warnings.
- User confirmation before persistence.

### Payments and expenses

- Full payments.
- Partial payments.
- Multiple payments.
- Invalid payment amounts.
- Business-level filtering.

### Financial analytics

- Receivables.
- Payables.
- Overdue invoices.
- Monthly performance.
- Forecasting.
- Missing historical data.
- Opening cash balance.

### Financial assistant

- Valid questions.
- Missing data.
- Groq failures.
- Business isolation.
- Correct serialization.

Use mocked external Groq calls in automated tests. Do not require a real API key to run the normal test suite.

Run the complete project test suite after implementation.

Also run the existing AI/ML tests:

`python -m pytest ai_ml/tests -v`

Do not claim integration is complete if tests have not actually been run.

---

# 15. IMPLEMENTATION RULES

Follow these rules throughout the task:

1. Inspect before editing.
2. Reuse existing code.
3. Preserve the existing AI/ML module.
4. Do not rewrite financial calculation logic.
5. Do not duplicate OCR or forecasting implementations.
6. Do not introduce unnecessary dependencies.
7. Do not introduce another backend framework.
8. Do not delete working functionality.
9. Do not use fake financial data in production code.
10. Do not bypass authentication or business authorization.
11. Do not automatically save AI-extracted invoices.
12. Do not expose secrets.
13. Use Decimal-compatible database fields for financial values.
14. Use database transactions where appropriate.
15. Keep code modular and maintainable.
16. Add meaningful tests.
17. Fix integration issues rather than hiding them.
18. Do not ask the user to manually create files that you can create yourself.
19. Do not stop after providing an implementation plan.
20. Do not commit or push changes unless explicitly authorized.

If a requirement cannot be implemented because the repository lacks necessary information, implement the safe parts first and clearly report the remaining blocker.

Do not invent business rules or database relationships.

---

# 16. FINAL EXECUTION PLAN

Work in the following order:

### Phase 1 — Repository audit

- Inspect project structure.
- Identify backend framework.
- Inspect existing models and routes.
- Inspect frontend API expectations.
- Inspect AI/ML interfaces.
- Produce a concise implementation plan.

### Phase 2 — Database and business logic

- Complete or extend database models.
- Implement relationships.
- Implement business-level data isolation.
- Add required migrations.
- Implement payment and expense handling.

### Phase 3 — Invoice integration

- Implement upload endpoints.
- Integrate OCR and extraction.
- Implement human review and confirmation.
- Implement invoice persistence.

### Phase 4 — Financial integration

- Connect receivables.
- Connect payables.
- Connect overdue invoice detection.
- Connect monthly performance.
- Connect cash-flow forecasting.
- Integrate actual opening cash balances.

### Phase 5 — Assistant integration

- Implement the assistant API.
- Retrieve authorized business data.
- Call the existing assistant function.
- Return serialized responses.
- Handle external AI service failures.

### Phase 6 — Security and testing

- Verify authentication.
- Verify business isolation.
- Verify upload security.
- Add backend tests.
- Run the complete test suite.
- Fix discovered issues.

### Phase 7 — Final report

Provide:

1. Backend files created.
2. Existing files modified.
3. Database models and relationships implemented.
4. API endpoints implemented.
5. AI/ML functions integrated.
6. Migrations created and their status.
7. Dependencies added or changed.
8. Environment variables required.
9. Commands to run the backend.
10. Test results, including actual pass/fail counts.
11. Remaining limitations or blockers.
12. Any manual steps still required.

Clearly distinguish completed work from work that remains.

---

# FINAL INSTRUCTION

**Start by inspecting the repository. Then implement the backend, not merely a design or tutorial.**

The existing `ai_ml/` directory is the established AI/ML implementation and must remain the source of truth for OCR, invoice extraction, validation, financial calculations, forecasting and financial assistant logic.

Build a secure, maintainable backend around it, following the repository's existing architecture.

The final result should be a working backend that can communicate with the existing frontend and AI/ML module, subject to the project's actual configuration and available services.
