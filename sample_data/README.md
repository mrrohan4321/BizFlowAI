# Sample data (synthetic only - never commit real invoices)

Shared by the whole team (used by the demo, the smoke test and the frontend checks).

Everything here is fictional. Real customer invoices must never be committed (`sample_data/real/` is git-ignored).

## `invoices/` - files for the upload demo (`POST /api/invoices/extract`)

| File | What it demonstrates |
|---|---|
| sales_INV-102_clean.png | clean image, sales invoice (the known-answer INV-102, Rs 30,000) |
| purchase_PUR-201.pdf | text PDF, purchase invoice (PUR-201, Rs 20,000) |
| sales_INV-103_total_mismatch.png | subtotal + tax != total -> a validation warning must be shown |
| sales_INV-104_blurry_scan.png | imperfect scan -> may need manual correction at review |

Suggested demo flow: upload `sales_INV-102_clean.png` -> review the extracted fields -> confirm -> it appears in the invoice list ->
record a 10,000 payment -> receivables drop from 45,000 to 35,000.

Note: the demo seed already contains INV-102, INV-103 and PUR-201. Saving the same number + type again returns
`409 duplicate_invoice`. To demo a fresh save, either use `INV-104`, change the invoice number in the review form,
or delete that invoice first (only possible while it has no payments).

## `synthetic/`

Reserved for generated test datasets (currently only `.gitkeep`). The 10 messy-invoice *test scenarios* used by the AI/ML tests live in
`ai_ml/tests/fixtures/messy_invoice_scenarios.json`.

## Database demo data

`database/seed_demo.sql` - see [../database/README.md](../database/README.md).
Used by `backend/scripts/smoke_test.py`, which uploads `sales_INV-102_clean.png` for the extraction check.
