# Sample data (synthetic only - never commit real invoices)

`invoices/` - fictional invoices for the upload demo (`POST /api/invoices/extract`):

| File | What it demonstrates |
|---|---|
| sales_INV-102_clean.png | clean image, sales invoice (the known-answer INV-102, Rs 30,000) |
| purchase_PUR-201.pdf | text PDF, purchase invoice (PUR-201, Rs 20,000) |
| sales_INV-103_total_mismatch.png | subtotal + tax != total -> a validation warning must be shown |
| sales_INV-104_blurry_scan.png | imperfect scan -> may need manual correction at review |

Database demo data lives in `database/seed_demo.sql`.
