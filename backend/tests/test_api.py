import getpass, json, urllib.error, urllib.request

SUPA = input("SUPABASE_URL: ").strip().rstrip("/")
ANON = input("Supabase anon (publishable) key: ").strip()
email = input("Email: ").strip()
pw = getpass.getpass("Password: ")
API = "https://bizflow-backend-2onh.onrender.com"

req = urllib.request.Request(
    f"{SUPA}/auth/v1/token?grant_type=password",
    json.dumps({"email": email, "password": pw}).encode(),
    {"apikey": ANON, "Content-Type": "application/json"},
)
try:
    token = json.load(urllib.request.urlopen(req))["access_token"]
except urllib.error.HTTPError as e:
    print("LOGIN FAILED:", e.code, e.read().decode())
    raise SystemExit(1)

def call(path):
    r = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(r, timeout=120) as x:
            return x.status, x.read().decode()[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

for p in ["/api/health", "/api/payments", "/api/invoices", "/api/analytics/summary"]:
    print("TOKEN:", token)
    print(p, call(p))