"""E2E test for Stock Manager API."""
import json
import http.client
import os
import sys
import time
import subprocess

DB_PATH = os.path.join(os.path.dirname(__file__), "yazmina_web.db")
HOST = "127.0.0.1"
PORT = 8765
COOKIE = None
passed = 0
failed = 0


def setup_db():
    sys.path.insert(0, os.path.dirname(__file__))
    from app.database import engine, Base, SessionLocal
    from app.models import AdminUser, SkuMaster
    from app.auth import hash_password
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(AdminUser).count() > 0:
            return
        db.add(AdminUser(username='admin', password_hash=hash_password('admin123')))
        db.add(SkuMaster(kode_sku='DG-Almond-L', nama_produk='DG Almond L', harga_jual=85000, kategori='Hijab'))
        db.add(SkuMaster(kode_sku='JSO-Mint-S', nama_produk='JSO Mint S', harga_jual=75000, kategori='Hijab'))
        db.add(SkuMaster(kode_sku='KRK-Dusty-M', nama_produk='KRK Dusty M', harga_jual=65000, kategori='Kerudung'))
        db.commit()
        print("[SETUP] Test data seeded.")
    finally:
        db.close()


def api(method, path, body=None, raw=False):
    global COOKIE
    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    headers = {"Content-Type": "application/json"}
    if COOKIE:
        headers["Cookie"] = COOKIE
    conn.request(method, path, json.dumps(body) if body else "", headers)
    res = conn.getresponse()
    data = res.read()
    for h in res.getheaders():
        if h[0].lower() == 'set-cookie':
            COOKIE = h[1].split(';')[0]
    conn.close()
    if raw:
        return res.status, data
    text = data.decode('utf-8', errors='replace')
    return res.status, json.loads(text) if text else {}


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} -- {detail}")


def run_tests():
    global COOKIE

    status, _ = api('POST', '/api/auth/login', {"username": "admin", "password": "admin123"})
    check("Login", status == 200, f"status={status}")

    # ── Test 1: List SKUs ────────────────────────────────────────
    print("\n[TEST 1] List SKUs")
    status, data = api('GET', '/api/stock/skus')
    check("List SKUs 200", status == 200, f"status={status}")
    check("Has 3 SKUs", isinstance(data, list) and len(data) == 3, f"got {len(data) if isinstance(data, list) else 'not list'}")

    # ── Test 2: Search SKUs ──────────────────────────────────────
    print("\n[TEST 2] Search SKUs")
    status, data = api('GET', '/api/stock/skus?search=DG')
    check("Search SKUs 200", status == 200, f"status={status}")
    check("Found DG SKU", len(data) >= 1 and data[0]['kode_sku'] == 'DG-Almond-L', f"got {data}")

    # ── Test 3: Export Stock IN ──────────────────────────────────
    print("\n[TEST 3] Export Stock IN")
    items = [
        {"sku": "DG-Almond-L", "qty": 10, "harga": 85000},
        {"sku": "JSO-Mint-S", "qty": 20, "harga": 75000},
    ]
    status, data = api('POST', '/api/stock/export', {"items": items, "mode": "stock_in"}, raw=True)
    check("Export IN returns 200", status == 200, f"status={status}")
    check("Export IN is Excel (xlsx bytes)", len(data) > 100 and data[:2] == b'PK', f"got {len(data)} bytes")

    # ── Test 4: Export Stock OUT ─────────────────────────────────
    print("\n[TEST 4] Export Stock OUT")
    status, data = api('POST', '/api/stock/export', {"items": items, "mode": "stock_out"}, raw=True)
    check("Export OUT returns 200", status == 200, f"status={status}")
    check("Export OUT is Excel", len(data) > 100 and data[:2] == b'PK', f"got {len(data)} bytes")

    # ── Test 5: Empty export fails ───────────────────────────────
    print("\n[TEST 5] Empty export")
    status, data = api('POST', '/api/stock/export', {"items": [], "mode": "stock_in"})
    check("Empty export returns 400", status == 400, f"status={status}")

    # ── Test 6: Auth required ────────────────────────────────────
    print("\n[TEST 6] Auth required")
    saved = COOKIE
    COOKIE = None
    status, _ = api('GET', '/api/stock/skus')
    check("Requires auth (401)", status == 401, f"status={status}")
    COOKIE = saved

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*40}")
    return failed == 0


if __name__ == "__main__":
    for _ in range(10):
        try:
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            break
        except PermissionError:
            time.sleep(0.5)
    setup_db()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=os.path.dirname(__file__),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(4)
    try:
        success = run_tests()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        for _ in range(10):
            try:
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                break
            except PermissionError:
                time.sleep(0.5)
    sys.exit(0 if success else 1)
