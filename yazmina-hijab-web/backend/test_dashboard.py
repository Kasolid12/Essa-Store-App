"""
E2E test for Dashboard API (Phase 6).
Tests: KPI queries, trend data, quick stats.
"""
import json
import http.client
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "yazmina_web.db")
HOST = "127.0.0.1"
PORT = 8765
BASE = f"{HOST}:{PORT}"
COOKIE = None


def setup_db():
    """Seed some test data into yazmina_web.db using SQLAlchemy ORM."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from app.database import engine, Base, SessionLocal
    from app.models import (
        AdminUser, SkuMaster, Person,
        ModalOperasional, PengeluaranOffline, DebtEntry, DebtPayment,
        SalaryRun, Client, ClientReceivable,
    )
    from app.auth import hash_password
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if data already exists
        if db.query(Person).count() > 0:
            return

        # Create admin user
        db.add(AdminUser(username='admin', password_hash=hash_password('admin123')))
        db.flush()

        supplier = Person(nama='Supplier A', person_type='SUPPLIER')
        klien = Person(nama='Klien B', person_type='KLIEN')
        karyawan = Person(nama='Karyawan C', person_type='KARYAWAN')
        db.add_all([supplier, klien, karyawan])
        db.flush()

        # DebtEntry (OPEN) — 5M hutang, 2M dibayar → sisa 3M
        de = DebtEntry(
            tipe_hutang='BARANG', tanggal='2026-08-15',
            person_id=supplier.id, keterangan='Hutang kain',
            nominal_hutang=5000000, status='OPEN',
        )
        db.add(de)
        db.flush()
        db.add(DebtPayment(debt_entry_id=de.id, tanggal_bayar='2026-08-20', nominal_bayar=2000000))

        # ClientReceivable (OPEN) — 3M piutang
        db.add(ClientReceivable(person_id=klien.id, nominal=3000000, sisa=3000000, status='OPEN'))

        # SalaryRun (PASUKAN_KARYAWAN)
        db.add(SalaryRun(tipe='PASUKAN_KARYAWAN', tanggal_proses='2026-08-25', gaji_kotor=1500000, gaji_bersih=1500000))

        # PengeluaranOffline — need an SKU first
        sku = SkuMaster(kode_sku='SKU-TEST', nama_produk='Produk Test', harga_jual=50000)
        db.add(sku)
        db.flush()
        db.add(PengeluaranOffline(tanggal='2026-08-22', sku_id=sku.id, qty=10, harga_satuan=50000, total=500000))

        # ModalOperasional
        db.add(ModalOperasional(tanggal='2026-08-18', jenis='BARANG', keterangan='Packaging', nominal=200000))

        db.commit()
        print("[SETUP] Test data seeded.")
    finally:
        db.close()


def api_get(path):
    global COOKIE
    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    headers = {"Content-Type": "application/json"}
    if COOKIE:
        headers["Cookie"] = COOKIE
    conn.request("GET", path, headers=headers)
    res = conn.getresponse()
    data = res.read().decode()
    # Capture cookie
    for h in res.getheaders():
        if h[0].lower() == 'set-cookie':
            COOKIE = h[1].split(';')[0]
    conn.close()
    return res.status, json.loads(data) if data else {}


def api_post(path, body):
    global COOKIE
    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    headers = {"Content-Type": "application/json"}
    if COOKIE:
        headers["Cookie"] = COOKIE
    conn.request("POST", path, json.dumps(body), headers)
    res = conn.getresponse()
    data = res.read().decode()
    for h in res.getheaders():
        if h[0].lower() == 'set-cookie':
            COOKIE = h[1].split(';')[0]
    conn.close()
    return res.status, json.loads(data) if data else {}


passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} -- {detail}")


def run_tests():
    global passed, failed, COOKIE

    # Login
    status, data = api_post("/api/auth/login", {"username": "admin", "password": "admin123"})
    check("Login", status == 200, f"status={status}")

    # ── Test 1: Main Dashboard KPIs ──────────────────────────────
    print("\n[TEST 1] Dashboard KPIs")
    status, data = api_get("/api/dashboard")
    check("Dashboard returns 200", status == 200, f"status={status}")
    check("total_hutang_tersisa = 3,000,000", data.get("total_hutang_tersisa") == 3_000_000, f"got {data.get('total_hutang_tersisa')}")
    check("total_piutang = 3,000,000", data.get("total_piutang") == 3_000_000, f"got {data.get('total_piutang')}")
    check("gaji_karyawan = 1,500,000", data.get("gaji_karyawan") == 1_500_000, f"got {data.get('gaji_karyawan')}")
    check("omzet = 500,000", data.get("omzet") == 500_000, f"got {data.get('omzet')}")
    check("penjualan_offline = 500,000", data.get("penjualan_offline") == 500_000, f"got {data.get('penjualan_offline')}")
    check("modal_operasional = 200,000", data.get("modal_operasional") == 200_000, f"got {data.get('modal_operasional')}")
    check("profit_produksi = -1,200,000", data.get("profit_produksi") == -1_200_000, f"got {data.get('profit_produksi')}")

    # ── Test 2: Dashboard with date filter ───────────────────────
    print("\n[TEST 2] Dashboard with date filter")
    status, data = api_get("/api/dashboard?mulai=2026-08-01&akhir=2026-08-31")
    check("Dashboard filtered 200", status == 200, f"status={status}")
    check("periode_mulai = 2026-08-01", data.get("periode_mulai") == "2026-08-01", f"got {data.get('periode_mulai')}")
    check("periode_akhir = 2026-08-31", data.get("periode_akhir") == "2026-08-31", f"got {data.get('periode_akhir')}")

    # ── Test 3: Monthly Trend ────────────────────────────────────
    print("\n[TEST 3] Monthly Trend")
    status, data = api_get("/api/dashboard/trend?months=3")
    check("Trend returns 200", status == 200, f"status={status}")
    check("Trend has 3 months", isinstance(data, list) and len(data) == 3, f"got {len(data) if isinstance(data, list) else 'not list'}")
    if isinstance(data, list) and len(data) > 0:
        check("Month has 'month' key", "month" in data[0], f"keys: {list(data[0].keys())}")
        check("Month has 'omzet' key", "omzet" in data[0], f"keys: {list(data[0].keys())}")
        check("Month has 'profit' key", "profit" in data[0], f"keys: {list(data[0].keys())}")

    # ── Test 4: Quick Stats ──────────────────────────────────────
    print("\n[TEST 4] Quick Stats")
    status, data = api_get("/api/dashboard/stats")
    check("Stats returns 200", status == 200, f"status={status}")
    check("hutang_open >= 1", data.get("hutang_open", 0) >= 1, f"got {data.get('hutang_open')}")
    check("piutang_open >= 1", data.get("piutang_open", 0) >= 1, f"got {data.get('piutang_open')}")

    # ── Test 5: Auth required ────────────────────────────────────
    print("\n[TEST 5] Auth required")
    old_cookie = COOKIE
    COOKIE = None
    status, _ = api_get("/api/dashboard")
    check("Dashboard requires auth (401)", status == 401, f"status={status}")
    COOKIE = old_cookie

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*40}")
    return failed == 0


if __name__ == "__main__":
    # Clean DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"[CLEAN] Removed {DB_PATH}")

    setup_db()
    print("\nStarting server...")
    import subprocess, time
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=os.path.dirname(__file__),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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
        import time as _time
        for _ in range(10):
            try:
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                    print(f"\n[CLEAN] Removed {DB_PATH}")
                break
            except PermissionError:
                _time.sleep(0.5)

    sys.exit(0 if success else 1)
