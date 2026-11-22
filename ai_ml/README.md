# 🧠 BizFlowAI — AI/ML Module

🌐 **Live API:** [bizflow-backend-2onh.onrender.com/docs](https://bizflow-backend-2onh.onrender.com/docs) · 🌍 **Live app:** [biz-flow-ai-xi.vercel.app](https://biz-flow-ai-xi.vercel.app/) · 🎬 **Demo video:** [YouTube](https://youtu.be/Tf-raKI9BRM)

**Owner: Rajdeep Panja (Member 3).** Integrated into the FastAPI backend by Rohan Adak (see the table at the end of section 10) and shown in the React app by Ronit Jana.

An AI-powered financial intelligence module for small businesses, built to support invoice processing, financial analysis, cash-flow forecasting, and natural-language financial assistance.

The module combines OCR, structured AI-based extraction, deterministic Python calculations, and an LLM-powered assistant.

**Core principle:** AI assists with understanding and explaining financial information, while Python performs the actual financial calculations.

---

## 📖 1. Overview

The AI/ML module provides:

| Capability | Description |
|---|---|
| Invoice OCR | Extracts text from PDF and image invoices |
| Invoice extraction | Uses Groq to identify structured invoice fields |
| Invoice validation | Checks extracted information using deterministic rules |
| Receivables analysis | Calculates outstanding customer payments |
| Payables analysis | Calculates outstanding supplier payments |
| Overdue detection | Identifies invoices with outstanding overdue balances |
| Financial analysis | Summarizes monthly income and outflows |
| Cash-flow forecasting | Estimates future cash flow using moving averages |
| Financial assistant | Answers financial questions using approved Python tools |

The module is independent of the database and frontend.

The backend retrieves authorized business data and supplies it to the AI/ML functions.

## 🏗️ 2. Architecture

```text
Frontend
   |
   v
Backend API
   |
   +-- Authentication
   |
   +-- Business authorization
   |
   +-- Database retrieval
   |
   v
AI/ML Module
   |
   +-----------------------+
   |                       |
   v                       v
Invoice Processing    Financial Analysis
   |                       |
   v                       v
OCR                    Python Metrics
   |                       |
   v                       v
Groq Extraction        Forecasting
   |                       |
   v                       |
Pydantic Validation        |
   |                       |
   +-----------+-----------+
               |
               v
        Structured Results
               |
               v
          Backend API
               |
               v
            Frontend
```

### 🎨 Design principles

- Deterministic financial calculations.
- Structured invoice extraction.
- Human review before invoice persistence.
- Separation of AI/ML and backend responsibilities.
- Business-level data isolation.
- Explainable forecasting.
- Restricted assistant tool execution.
- No LLM-generated SQL or financial arithmetic.

## 📁 3. Project structure

```text
ai_ml/
├── __init__.py
├── README.md
├── .gitignore
├── config.py
├── schemas.py
├── ocr.py
├── invoice_extraction.py
├── validation.py
├── finance_metrics.py
├── forecasting.py
├── assistant_tools.py
├── assistant.py
└── tests/
    ├── README.md
    ├── fixtures/
    │   └── messy_invoice_scenarios.json
    ├── test_config.py
    ├── test_schemas.py
    ├── test_ocr.py
    ├── test_invoice_extraction.py
    ├── test_validation.py
    ├── test_finance_metrics.py
    ├── test_forecasting.py
    ├── test_assistant_tools.py
    ├── test_assistant.py
    └── test_messy_invoice_dataset.py
```

### 📌 Module responsibilities

| File | Responsibility |
|---|---|
| `config.py` | Environment configuration and runtime settings |
| `schemas.py` | Pydantic data models |
| `ocr.py` | PDF and image text extraction |
| `invoice_extraction.py` | Groq-powered invoice extraction |
| `validation.py` | Deterministic invoice validation |
| `finance_metrics.py` | Financial calculations and overdue detection |
| `forecasting.py` | Moving-average forecasting |
| `assistant_tools.py` | Approved deterministic assistant tools |
| `assistant.py` | Natural-language financial assistant |
| `tests/fixtures/messy_invoice_scenarios.json` | Synthetic invoice test scenarios |
| `tests/test_messy_invoice_dataset.py` | Tests for the synthetic invoice dataset |

## 🧰 4. Technology stack

The AI/ML module uses:

- Python 3.12
- Groq API
- Pydantic 2
- RapidOCR
- PyMuPDF
- Pillow
- python-dotenv
- Decimal-based financial calculations
- pytest

Configured Groq model:

`openai/gpt-oss-120b`

The model can be changed through environment configuration.

## ⚙️ 5. Installation and configuration

Run commands from the project root.

### 📌 Install dependencies

Install the project's backend dependencies:

```powershell
pip install -r backend/requirements.txt
```

The AI/ML module additionally requires RapidOCR and PyMuPDF.

Install the tested versions:

```powershell
pip install rapidocr==3.10.0 PyMuPDF==2.1
```

Other shared dependencies are already included in the backend requirements.

Use the project's tested Python environment and dependency versions.

### 🔧 Environment variables

Create a `.env` file in the project root.

Example:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
GROQ_TIMEOUT_SECONDS=30
MIN_TEXT_CHARS_PER_PAGE=30
AMOUNT_TOLERANCE=1.00
```

Never commit the actual `.env` file or expose API keys in source code.

The configuration module loads environment variables from:

1. Project root `.env`
2. `ai_ml/.env`

Existing environment variables take priority.

The Groq API key is required when a Groq-powered operation executes, not merely when importing the package.

### ⚙️ Configuration reference

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Groq API authentication |
| `GROQ_MODEL` | Model used for AI operations |
| `GROQ_TIMEOUT_SECONDS` | API request timeout |
| `MIN_TEXT_CHARS_PER_PAGE` | Threshold for sparse PDF text |
| `AMOUNT_TOLERANCE` | Tolerance for invoice amount validation |

## 🔎 6. Invoice OCR and extraction

### 🔎 OCR

File: `ocr.py`

Supported formats:

- PDF
- JPG
- JPEG
- PNG

The OCR implementation uses:

- PyMuPDF for PDF processing.
- RapidOCR for image text recognition.
- Direct PDF text extraction before OCR where possible.

Scanned or text-sparse PDF pages are processed through OCR.

Image inputs are checked before processing.

Temporary OCR files are cleaned up after use.

Unsupported files and password-protected PDFs produce explicit errors.

### 📌 Invoice extraction

File: `invoice_extraction.py`

Main function:

```python
from ai_ml.invoice_extraction import extract_invoice

result = extract_invoice(
    "sample_data/invoices/sample_invoice.png"
)

print(result.model_dump())
```

Pipeline:

1. Extract invoice text using OCR.
2. Send OCR text to Groq.
3. Request structured JSON.
4. Validate extracted values using Pydantic.
5. Run deterministic invoice validation.
6. Return the result for human review.

### 📌 Extracted fields

The `InvoiceFields` schema supports:

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

Rules:

- Missing values remain `None`.
- Invoice type is `sales`, `purchase`, or `None`.
- Dates are represented as Python `date` values.
- Monetary fields use Python `Decimal`.
- Supported currency prefixes include ₹, Rs, and INR.
- Both Indian and international comma grouping are supported.
- Invalid monetary values are rejected.

### 📌 Extraction result

`extract_invoice()` returns an `InvoiceExtractionResult` containing:

| Field | Description |
|---|---|
| `fields` | Extracted `InvoiceFields` |
| `issues` | Validation issues |
| `needs_review` | Whether human review is required |
| `source_file` | Source file path |
| `raw_text_preview` | OCR text preview, limited to 1,000 characters |

**Important:** Successful extraction does not mean the invoice is approved.

`needs_review` remains `True`. The backend must provide a human-review workflow and must not automatically save an extracted invoice as an approved record.

### 🚨 Error handling

OCR and file-processing errors propagate to the caller.

AI extraction failures return an `InvoiceExtractionResult` with:

- Empty invoice fields.
- An error issue.
- `needs_review=True`.
- Source file information.
- Available OCR preview.

The backend should handle OCR exceptions and present appropriate feedback to the user.

## ✅ 7. Invoice validation

File: `validation.py`

Main function:

```python
from ai_ml.validation import validate_invoice

issues = validate_invoice(invoice_fields)
```

Validation is deterministic and checks invoice consistency, including:

- Missing required information.
- Negative monetary amounts.
- Subtotal, tax, and total consistency.
- GST component structure.
- Date consistency.
- GSTIN format.

Validation issues use the `ValidationIssue` schema:

- `field`
- `severity`
- `message`

Severity values:

- `error`
- `warning`

Validation is not a government GST database lookup and does not establish legal tax compliance.

## 📊 8. Financial metrics

File: `finance_metrics.py`

Financial calculations use Python `Decimal` to reduce floating-point rounding errors.

Important functions:

```python
from ai_ml.finance_metrics import (
    calculate_business_summary,
    get_overdue_invoices,
    outstanding,
    invoice_status,
    is_overdue,
)
```

### 📌 Business summary

```python
summary = calculate_business_summary(
    business_id="business-001",
    invoices=invoices,
    payments=payments,
    expenses=expenses,
)
```

The summary calculates:

- Sales total.
- Expense total.
- Receivables.
- Payables.
- Operating surplus estimate.

Records are filtered using the supplied business ID.

### 📌 Overdue invoices

```python
overdue = get_overdue_invoices(
    business_id="business-001",
    invoices=invoices,
    payments=payments,
    today=date.today(),
)
```

The function identifies invoices with outstanding balances past their due dates.

Returned records include invoice identifiers, party information, outstanding amounts, and days overdue.

The backend must provide authorized business-scoped records.

## 📈 9. Cash-flow forecasting

File: `forecasting.py`

The forecasting module uses a recent-month moving-average baseline.

By default, it uses up to **12 recent historical months** to calculate average income and outflows.

Main function:

```python
from ai_ml.forecasting import get_forecast

forecast = get_forecast(
    monthly_history=monthly_history,
    opening_cash=50000,
    forecast_months=3,
    window=12,
)
```

Arguments:

| Argument | Description |
|---|---|
| `monthly_history` | Historical monthly income and outflows |
| `opening_cash` | Actual opening cash balance |
| `forecast_months` | Number of future months |
| `window` | Number of recent months used for averages; default is 12 |

If fewer than 12 historical months are available, the forecasting function uses all available months rather than requiring 12 months of data.

The forecast estimates future:

- Income.
- Outflows.
- Closing cash.

The result includes forecast periods, assumptions, the method used, and closing cash.

### ⚠️ Important limitations

- A moving average is a baseline, not a guarantee.
- Forecast quality depends on the quality and length of historical data.
- The backend must provide the actual opening cash balance.
- Missing opening cash must not be silently treated as a verified zero balance.
- The AI/ML module cannot generate missing real historical financial records.
- The backend must supply the available historical financial data.
- Forecasts must be presented as estimates, not guaranteed outcomes.

## 💬 10. Financial assistant

File: `assistant.py`

Main function:

```python
from ai_ml.assistant import answer_finance_question

response = answer_finance_question(
    question="How much money do my customers owe me?",
    business_id="business-001",
    invoices=invoices,
    payments=payments,
)
```

### 📌 Approved tools

The assistant can select from five approved Python tools:

| Tool | Purpose |
|---|---|
| `get_receivables_summary` | Customer outstanding balances |
| `get_payables_summary` | Supplier outstanding balances |
| `get_overdue_invoices` | Overdue invoice analysis |
| `get_monthly_performance` | Historical monthly performance |
| `get_cash_forecast` | Future cash-flow estimation |

Groq selects a tool and explains the calculated result.

Python performs the financial calculations.

The LLM does not execute SQL or independently calculate financial totals.

### 📌 Greetings, capability questions and out-of-scope questions

When the question does not need a financial tool, the assistant does **not** call Groq. `_fallback_answer()` returns a fixed, friendly answer:

| Question type | Examples | Result |
|---|---|---|
| Greeting | "hi", "hello", "good morning" | short welcome that lists what can be asked |
| Capability | "what can you do?", "how can you help me?" | numbered list of the five supported areas |
| Out of scope | "Should I buy bitcoin?" | polite redirect to finance topics |

All three return `tool_used=None`, `data=None` and `insufficient_data=False`. `insufficient_data=True` is reserved for missing data
(for example no history for the forecast) or an unavailable AI service.

### 📌 Backend arguments

`answer_finance_question()` accepts:

| Argument | Required when | Description |
|---|---|---|
| `question` | Always | User's financial question |
| `business_id` | Always | Authenticated business identifier |
| `invoices` | Receivables, payables, overdue | Business-scoped invoice records |
| `payments` | Receivables, payables, overdue | Business-scoped payment records |
| `expenses` | Accepted by function | Business-scoped expense records |
| `monthly_history` | Monthly performance and forecast | Historical monthly financial records |
| `opening_cash` | Forecast | Actual opening cash balance |
| `today` | Optional | Date override for overdue calculations |
| `forecast_months` | Optional | Forecast horizon, default 3 |
| `forecast_window` | Optional | Moving-average window, default 12 historical months |

The current assistant does not independently expose an expense-specific tool. The `expenses` parameter is accepted but is not currently passed into the five registered assistant tools.

### 🔗 Backend integration example

```python
from ai_ml.assistant import answer_finance_question

response = answer_finance_question(
    question=user_question,
    business_id=authenticated_business.id,
    invoices=business_invoices,
    payments=business_payments,
)

return response.model_dump(mode="json")
```

This is an example of the integration pattern. The backend must implement authentication, authorization, database retrieval, and business-level filtering.

### 💬 Assistant response

The function returns an `AssistantResponse` containing:

- `question`
- `answer`
- `tool_used`
- `data`
- `insufficient_data`

The `data` field contains the actual result from the approved Python tool.

If Groq fails during answer generation, the calculated financial result is preserved and a fallback explanation is returned.

### ✅ How the backend uses this module (status: integrated)

| ai_ml function | Called from `backend/app/services/` | Used for |
|---|---|---|
| `invoice_extraction.extract_invoice` | `invoices.py` | `POST /api/invoices/extract` (result goes to a staging table, never straight into `invoices`) |
| `validation.validate_invoice`, `schemas.InvoiceFields` | `invoices.py` | `POST /api/invoices`, `PATCH /api/invoices/{id}` |
| `finance_metrics.outstanding`, `invoice_status`, `money` | `payments.py` | balance and status of every invoice, overpayment check |
| `finance_metrics.calculate_business_summary` | `analytics.py` | `GET /api/analytics/summary` |
| `assistant_tools.get_overdue_invoices_tool` | `analytics.py` | `GET /api/analytics/overdue` |
| `assistant_tools.get_monthly_performance` | `analytics.py` | cash summary in `GET /api/analytics/monthly` |
| `forecasting.get_forecast` | `analytics.py` | `GET /api/forecast` (the API route defaults to `window=3`; this module defaults to 12) |
| `assistant.answer_finance_question` | `assistant.py` | `POST /api/assistant/chat` |

The backend sends only the authenticated business's records, passes the real opening cash (and returns `409` if it is missing, never zero),
and builds monthly history from actual payments and expenses marked paid. Do not change these function signatures without updating
`backend/app/services/` and its tests. See [../backend/README.md](../backend/README.md).

## 🔗 11. Backend integration responsibilities

The AI/ML module does not:

- Authenticate users.
- Authorize business access.
- Connect to the application database.
- Save invoices.
- Manage payments.
- Manage user accounts.
- Expose API routes.
- Render frontend components.

These responsibilities belong to the backend and frontend.

### 📌 Mandatory backend responsibilities

1. Authenticate the current user.
2. Identify the user's authorized business.
3. Retrieve only records belonging to that business.
4. Pass business-scoped data into AI/ML functions.
5. Validate and review extracted invoices before persistence.
6. Handle exceptions and return appropriate API responses.
7. Preserve monetary precision when storing and transferring financial values.
8. Supply actual opening cash for forecasts.
9. Never trust a client-supplied business ID without authorization checks.

**Business isolation must be enforced by the backend, not by the LLM.**

## 🔒 12. Security considerations

- Keep Groq API credentials in environment variables.
- Never expose secrets in frontend code.
- Do not commit `.env` files.
- Treat OCR invoice content as untrusted input.
- Do not follow instructions embedded in invoice text.
- Do not allow LLM-generated SQL.
- Do not execute arbitrary tools selected outside the approved registry.
- Enforce business authorization before passing records into AI/ML functions.
- Require human review before invoice persistence.

## 🧪 13. Testing

Run tests from the project root:

```powershell
python -m pytest .\ai_ml\tests -v
```

Run the complete suite quietly:

```powershell
python -m pytest .\ai_ml\tests -q
```

The test files and fixtures are described in [tests/README.md](tests/README.md). No API key or database is needed.

Run only the synthetic invoice dataset tests:

```powershell
python -m pytest .\ai_ml\tests\test_messy_invoice_dataset.py -v
```

Run forecasting tests:

```powershell
python -m pytest .\ai_ml\tests\test_forecasting.py -v
```

Compile the module:

```powershell
python -m compileall -q .\ai_ml
```

Check whitespace errors:

```powershell
git diff --check
```

### 🧬 Synthetic invoice dataset

The test fixture `tests/fixtures/messy_invoice_scenarios.json` contains 10 synthetic invoice scenarios designed to exercise invoice schema parsing and deterministic validation.

The scenarios cover:

1. Valid sales invoice.
2. Missing invoice number.
3. Invalid GSTIN format.
4. Incorrect invoice total.
5. CGST and SGST mismatch.
6. IGST and CGST used together.
7. Due date before invoice date.
8. Negative subtotal.
9. Malformed monetary amount.
10. Missing due date.

The dataset tests check whether each scenario produces the expected schema error or validation issues.

These are synthetic test cases, not real customer invoices. They help verify how the module handles both ordinary and problematic invoice data.

The AI/ML module has been tested with unit tests and live Groq/OCR integration checks.

## ⚠️ 14. Known limitations

- Invoice extraction depends on OCR quality and Groq availability.
- Extracted values require human review.
- Invoice validation is deterministic but does not verify invoices against government databases.
- Forecasting uses a moving-average baseline and is not a guarantee of future cash flow.
- Forecasting can use up to 12 months of supplied history; it cannot create missing historical records.
- Assistant answers depend on the accuracy of backend-supplied records.
- Currency display must be based on explicitly supplied currency information.
- The current assistant supports five registered financial tools.

## ⚡ 15. Quick reference

| Task | Function |
|---|---|
| OCR invoice | `extract_invoice_text()` |
| Extract invoice fields | `extract_invoice_fields()` |
| Full invoice extraction | `extract_invoice()` |
| Validate invoice | `validate_invoice()` |
| Calculate business summary | `calculate_business_summary()` |
| Find overdue invoices | `get_overdue_invoices()` |
| Generate cash forecast | `get_forecast()` |
| Answer finance question | `answer_finance_question()` |

---

**BizFlowAI AI/ML Module**

AI for understanding. Python for calculations. Backend for security and persistence. Human review for invoice approval.
