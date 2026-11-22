# 🧪 ai_ml/tests

Owner: Rajdeep Panja. Run from the **repo root**:

```bash
python -m pytest ai_ml/tests -v
```

No database, no API key and no internet are needed: Groq and OCR calls are mocked.

| File | Covers |
|---|---|
| `test_config.py` | environment settings and defaults |
| `test_schemas.py` | Pydantic models, money/date cleaning (for example `₹1,23,456.78`), malformed values |
| `test_ocr.py` | PDF/image text extraction paths and failures |
| `test_invoice_extraction.py` | extraction flow with a mocked Groq, error results |
| `test_validation.py` | deterministic invoice checks (totals, GST, dates, GSTIN) |
| `test_finance_metrics.py` | summary, receivables/payables, outstanding, status, overdue detection |
| `test_forecasting.py` | moving average, 12-month default window, fewer months than the window, insufficient data |
| `test_assistant_tools.py` | the five approved assistant tools |
| `test_assistant.py` | tool selection, greetings / capability / out-of-scope answers, Groq failures, insufficient data |
| `test_messy_invoice_dataset.py` | runs every case from `fixtures/messy_invoice_scenarios.json` through schema + validation |

## 🧬 fixtures/messy_invoice_scenarios.json

10 **synthetic** invoice scenarios (valid invoice, missing number, bad GSTIN, wrong total, CGST/SGST mismatch, IGST mixed with CGST,
due date before invoice date, negative subtotal, malformed amount, missing due date). Each case lists the schema error or the exact
`(field, severity)` validation issues it must produce; case ids must be unique.

To add a scenario: append a case to the JSON file with `id`, `invoice`, `expected_schema_error` and `expected_issues`, then run the tests.
