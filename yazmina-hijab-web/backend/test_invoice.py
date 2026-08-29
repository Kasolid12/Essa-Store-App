"""E2E test for Invoice & Piutang API."""
import sys, os, json, time, subprocess, http.cookiejar, urllib.request

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Clean DB
for f in ['yazmina_web.db', 'yazmina_web.db-wal', 'yazmina_web.db-shm']:
    if os.path.exists(f):
        try: os.remove(f)
        except: pass

# Start server
proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8765'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
time.sleep(3)

BASE = 'http://127.0.0.1:8765'

# Setup: create admin
subprocess.run([sys.executable, 'create_admin.py', '--auto'], capture_output=True)

# Login
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
login_data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode()
req_login = urllib.request.Request(BASE + '/api/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
resp = opener.open(req_login)
print(f"Login: {resp.status}")

passed = 0
failed = 0

def api_get(path):
    r = urllib.request.Request(BASE + path, headers={'Content-Type': 'application/json'})
    resp = opener.open(r)
    return resp.status, json.loads(resp.read())

def api_post(path, body):
    data = json.dumps(body).encode()
    r = urllib.request.Request(BASE + path, data=data, headers={'Content-Type': 'application/json'})
    r.method = 'POST'
    resp = opener.open(r)
    return resp.status, json.loads(resp.read())

def api_delete(path):
    r = urllib.request.Request(BASE + path, method='DELETE')
    resp = opener.open(r)
    try:
        return resp.status, json.loads(resp.read())
    except:
        return resp.status, {}

def test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS  {name}")
    except AssertionError as e:
        failed += 1
        print(f"  FAIL  {name}: {e}")
    except Exception as e:
        failed += 1
        print(f"  ERROR {name}: {e}")

print("\n=== Invoice & Piutang E2E ===\n")

# Create client
s, d = api_post("/api/clients", {"nama": "Toko Budi", "alamat": "Jakarta", "no_hp": "08123"})
assert s == 201, f"Create client: {s} {d}"
client_id = d["id"]
print(f"  Created client id={client_id}")

# Create person (KLIEN)
s, d = api_post("/api/persons", {"nama": "Pak Joko", "person_type": "KLIEN"})
assert s in (200, 201), f"Create person: {s} {d}"
person_id = d["id"]
print(f"  Created person id={person_id}")

# Create SKU
s, d = api_post("/api/sku", {"kode_sku": "INV-SKU-1", "nama_produk": "Produk Invoice"})
assert s in (200, 201), f"Create SKU: {s} {d}"
sku_id = d["id"]

# Sale for client
s, d = api_post("/api/pengeluaran-offline", {
    "tanggal": "2026-08-28", "sku_id": sku_id, "qty": 10,
    "harga_satuan": 50000, "total": 500000, "client_id": client_id,
})
assert s in (200, 201), f"Sale (client): {s} {d}"
print(f"  Sale (client): Rp 500,000")

# Sale for person
s, d = api_post("/api/pengeluaran-offline", {
    "tanggal": "2026-08-28", "sku_id": sku_id, "qty": 5,
    "harga_satuan": 50000, "total": 250000, "person_id": person_id,
})
assert s in (200, 201), f"Sale (person): {s} {d}"
print(f"  Sale (person): Rp 250,000")

# List invoice clients
s, d = api_get("/api/invoice/clients")
assert s == 200 and len(d) >= 2, f"Clients: {s} {len(d)}"
print(f"  Invoice clients: {len(d)}")

client_ref = f"client_{client_id}"

# Combined table
s, d = api_get(f"/api/invoice/combined/{client_ref}")
assert s == 200 and len(d["rows"]) == 1
assert d["rows"][0]["debit"] == 500000
assert d["rows"][0]["status"] == "BELUM LUNAS"
print(f"  Combined: 1 row, debit=500000, status=BELUM LUNAS")

# Summary
s, d = api_get(f"/api/invoice/summary/{client_ref}")
assert d["total_tagihan"] == 500000
assert d["sisa"] == 500000
assert d["status"] == "BELUM LUNAS"
print(f"  Summary: tagihan=500000, sisa=500000, BELUM LUNAS")

# Deposit partial
s, d = api_post(f"/api/invoice/deposit/{client_ref}", {
    "tanggal_bayar": "2026-08-28", "nominal_bayar": 200000, "metode": "CASH"
})
assert s == 200
print(f"  Deposit Rp 200,000")

# Verify
s, d = api_get(f"/api/invoice/summary/{client_ref}")
assert d["total_bayar"] == 200000
assert d["sisa"] == 300000
assert d["status"] == "BELUM LUNAS"
print(f"  After deposit: bayar=200000, sisa=300000")

# Full payment
s, d = api_post(f"/api/invoice/deposit/{client_ref}", {
    "tanggal_bayar": "2026-08-29", "nominal_bayar": 300000, "metode": "TRANSFER"
})
assert s == 200

# Verify LUNAS
s, d = api_get(f"/api/invoice/summary/{client_ref}")
assert d["sisa"] == 0
assert d["status"] == "LUNAS"
print(f"  Full paid: LUNAS")

# Delete a payment
s, d = api_get(f"/api/invoice/combined/{client_ref}")
payments = [r for r in d["rows"] if r["jenis"] == "Pembayaran"]
assert len(payments) == 2
pay_id = int(payments[0]["id"].replace("P", ""))
s, d = api_delete(f"/api/invoice/payment/{pay_id}")
assert s == 200
print(f"  Deleted payment id={pay_id}")

# Verify after delete
s, d = api_get(f"/api/invoice/summary/{client_ref}")
assert d["sisa"] > 0
print(f"  After delete: sisa={d['sisa']}, status={d['status']}")

# Person ref
person_ref = f"person_{person_id}"
s, d = api_get(f"/api/invoice/summary/{person_ref}")
assert d["total_tagihan"] == 250000
print(f"  Person summary: tagihan=250000")

# Cleanup
proc.terminate()
try: proc.wait(timeout=3)
except: proc.kill()

for f in ['yazmina_web.db', 'yazmina_web.db-wal', 'yazmina_web.db-shm']:
    try: os.remove(f)
    except: pass

print(f"\n=== {passed} passed, {failed} failed ===\n")
sys.exit(0 if failed == 0 else 1)
