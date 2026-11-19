"""Manual end-to-end check of a RUNNING BizFlow backend (local or Render). Not a pytest test.

    python backend/scripts/smoke_test.py                 # asks for login details
    python backend/scripts/smoke_test.py --skip-ai       # skip the Groq-dependent steps
    BIZFLOW_API=http://localhost:8000 python backend/scripts/smoke_test.py

Optional env vars: BIZFLOW_API, BIZFLOW_TOKEN (skip login), SUPABASE_URL, SUPABASE_ANON_KEY, BIZFLOW_EMAIL.
Read-only: it never saves or changes any record. The access token is never printed.
"""
import argparse
import getpass
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DEFAULT_API = "https://bizflow-backend-2onh.onrender.com"
SAMPLE = Path(__file__).resolve().parents[2] / "sample_data" / "invoices" / "sales_INV-102_clean.png"
results: list[tuple[str, str]] = []


def say(tag: str, msg: str):
    results.append((tag, msg))
    print(f"[{tag}] {msg}", flush=True)


def call(api, method, path, token=None, body=None, raw=None, ctype=None, timeout=120):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = raw
    if body is not None:
        data, ctype = json.dumps(body).encode(), "application/json"
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(api + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, text = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode()
    except Exception as e:  # network / timeout
        return 0, {"error": {"message": f"{type(e).__name__}: {e}"}}
    try:
        return status, json.loads(text)
    except ValueError:
        return status, {"raw": text[:200]}


def err(payload) -> str:
    e = payload.get("error") if isinstance(payload, dict) else None
    return f"{e.get('code', '')} {e.get('message', '')}".strip() if isinstance(e, dict) else str(payload)[:150]


def login() -> str:
    if os.getenv("BIZFLOW_TOKEN"):
        return os.environ["BIZFLOW_TOKEN"]
    supa = (os.getenv("SUPABASE_URL") or input("SUPABASE_URL (https://xxx.supabase.co): ")).strip().rstrip("/")
    anon = (os.getenv("SUPABASE_ANON_KEY") or input("Supabase anon/publishable key: ")).strip()
    email = (os.getenv("BIZFLOW_EMAIL") or input("Email: ")).strip()
    pw = getpass.getpass("Password: ")
    req = urllib.request.Request(f"{supa}/auth/v1/token?grant_type=password",
                                 json.dumps({"email": email, "password": pw}).encode(),
                                 {"apikey": anon, "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"LOGIN FAILED ({e.code}): {e.read().decode()[:200]}")


def multipart(field, path: Path):
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    head = (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{path.name}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n").encode()
    return head + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.getenv("BIZFLOW_API", DEFAULT_API))
    ap.add_argument("--skip-ai", action="store_true", help="skip assistant + invoice extraction (need Groq)")
    a = ap.parse_args()
    api = a.api.rstrip("/")
    print(f"Testing {api}\n(first request can take ~1 minute if the Render free service was asleep)\n")

    st, j = call(api, "GET", "/api/health", timeout=150)
    if st == 200 and j.get("database") is True:
        say("PASS", "health: server up and database connected")
    else:
        say("FAIL", f"health: HTTP {st} {j}"); return finish()

    token = login()
    st, j = call(api, "GET", "/api/analytics/summary", token)
    if st == 200:
        known = j["receivables"] == 45000 and j["payables"] == 20000
        say("PASS", f"summary: receivables {j['receivables']}, payables {j['payables']}, sales {j['sales_total']}"
                    + (" (matches the demo known answer)" if known else " (differs from demo seed - fine if you changed data)"))
    else:
        say("FAIL", f"summary: HTTP {st} {err(j)}" + ("  -> token rejected: check SUPABASE_URL / SUPABASE_JWT_SECRET on the server" if st == 401 else ""))

    st, j = call(api, "GET", "/api/payments/overdue", token)
    say("PASS" if st == 200 else "FAIL", f"overdue: {j.get('count')} overdue invoice(s)" if st == 200 else f"overdue: HTTP {st} {err(j)}")

    st, j = call(api, "GET", "/api/invoices?limit=5", token)
    say("PASS" if st == 200 else "FAIL", f"invoices: {j.get('total')} on record" if st == 200 else f"invoices: HTTP {st} {err(j)}")

    st, j = call(api, "GET", "/api/forecast", token)
    if st == 200:
        say("PASS" if not j["insufficient_data"] else "WARN",
            f"forecast: {j['method']}, periods {j['periods']}" + (f", warnings {j['warnings']}" if j["warnings"] else ""))
    elif st == 409:
        say("WARN", "forecast: opening cash not set (PUT /api/opening-cash with a month-end date)")
    else:
        say("FAIL", f"forecast: HTTP {st} {err(j)}")

    if a.skip_ai:
        say("INFO", "assistant + extraction skipped (--skip-ai)"); return finish()

    st, j = call(api, "POST", "/api/assistant/chat", token, body={"question": "How much do my customers owe me?"})
    if st == 200:
        say("PASS", f"assistant: tool={j.get('tool_used')}, insufficient_data={j.get('insufficient_data')}, answer: {str(j.get('answer'))[:120]}")
    else:
        say("FAIL", f"assistant: HTTP {st} {err(j)}" + ("  -> GROQ_API_KEY missing/invalid on the server" if st == 503 else ""))

    if not SAMPLE.exists():
        say("WARN", f"extraction skipped: {SAMPLE} not found"); return finish()
    body, ctype = multipart("file", SAMPLE)
    t = time.time()
    st, j = call(api, "POST", "/api/invoices/extract", token, raw=body, ctype=ctype, timeout=180)
    took = time.time() - t
    if st == 200:
        f = j.get("extracted_fields") or {}
        ok = j.get("extraction_status") == "ok"
        say("PASS" if ok else "WARN",
            f"extract ({took:.0f}s): status={j.get('extraction_status')}, invoice_number={f.get('invoice_number')}, "
            f"total={f.get('total_amount')}, warnings={len(j.get('warnings') or [])} (nothing was saved)")
    else:
        say("FAIL", f"extract: HTTP {st} {err(j)}" + ("  -> server may have run out of memory (free plan 512 MB)" if st in (0, 502, 503) else ""))
    finish()


def finish():
    fails = sum(1 for t, _ in results if t == "FAIL")
    warns = sum(1 for t, _ in results if t == "WARN")
    print(f"\n{'ALL GOOD' if not fails else 'PROBLEMS FOUND'}: {fails} failed, {warns} warning(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
