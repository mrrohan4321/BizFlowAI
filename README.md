# BizFlow AI
AI-powered finance assistant for small businesses. Team Finnovate - Arthaton 2026.

## Features
Invoice upload -> OCR + AI extraction -> human review -> save -> dashboard -> payments -> grounded assistant -> cash-flow estimate.

## Stack
React + Vite + Tailwind | FastAPI + Pydantic | Supabase PostgreSQL | Tesseract/EasyOCR | Groq LLM | Pandas + scikit-learn

## Structure
- `frontend/`  React app
- `backend/`   FastAPI app
- `ai_ml/`     OCR, extraction, validation, metrics, forecast, assistant tools
- `database/`  schema.sql, seed_demo.sql
- `sample_data/` synthetic invoices and records only

## Setup
```bash
# 1. backend
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env          # fill DATABASE_URL, SUPABASE_URL (+ SUPABASE_JWT_SECRET for HS256 projects), GROQ_API_KEY
python -m app.db.migrate            # creates tables (schema.sql + migrations)
uvicorn app.main:app --reload       # API docs: http://localhost:8000/docs

# 2. demo data (optional): edit demo_user in database/seed_demo.sql, then run it in the Supabase SQL Editor

# 3. frontend
cd frontend && npm install && npm run dev
```

## Getting a token for Swagger (/docs -> Authorize)
Create a user in Supabase (Authentication -> Users), then:
```bash
curl -X POST "$SUPABASE_URL/auth/v1/token?grant_type=password" -H "apikey: <anon key>" \
  -H "Content-Type: application/json" -d '{"email":"you@example.com","password":"..."}'
```
Paste the `access_token` into **Authorize**.

## Tests
```bash
cd backend && TEST_DATABASE_URL=postgresql://... python -m pytest tests -v   # runs in a throw-away schema
python -m pytest ai_ml/tests -v                                              # from the repo root
```
Groq is mocked; no API key is needed for tests.

## Environment variables
See `.env.example`.

## Architecture / Screenshots / Team
TODO
