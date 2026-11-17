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
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # fill values
uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev
```

## Environment variables
See `.env.example`.

## Architecture / Screenshots / Team
TODO
