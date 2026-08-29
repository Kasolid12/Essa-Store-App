"""E2E test for Profit Simulation API."""
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
    from app.models import (
        AdminUser, SkuMaster, Person, HasilCutting, DistribusiCutting,
        DebtEntry, TarifMaster,
    )
    from app.auth import hash_password
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(Person).count() > 0:
            return

        db.add(AdminUser(username='admin', password_hash=hash_password('admin123')))

        supplier = Person(nama='Supplier A', person_type='SUPPLIER')
        penjahit = Person(nama='Penjahit B', person_type='PENJAHIT')
        pengsup = Person(nama='Pengsup C', person_type='SUPPLIER')
        db.add_all([supplier, penjahit, pengsup])
        db.flush()

        sku1 = SkuMaster(kode_sku='DG-Almond-L', nama_produk='DG Almond L', harga_jual=85000)
        sku2 = SkuMaster(kode_sku='JSO-Mint-S', nama_produk='JSO Mint S', harga_jual=75000)
        db.add_all([sku1, sku2])
        db.flush()

        # Tarif
        db.add(TarifMaster(kode_sku='DG-Almond-L', tarif_jahit=1200, tarif_pengsup_potongan=2000))
        db.add(TarifMaster(kode_sku='JSO-Mint-S', tarif_jahit=900, tarif_pengsup_potongan=1800))

        # DebtEntry MODAL (kain)
        de = DebtEntry(
            tipe_hutang='MODAL', tanggal='2026-08-10',
            person_id=supplier.id, keterangan='Kain batch 2026-08',
            nominal_hutang=3000000, qty=50, status='OPEN',
            kode_produksi='BATCH-2026-08', status_cutting='OPEN',
        )
        db.add(de)
        db.flush()

        # Hasil Cutting
        db.add(HasilCutting(tanggal='2026-08-12', kode_produksi='BATCH-2026-08', sku_id=sku1.id, qty=200))
        db.add(HasilCutting(tanggal='2026-08-13', kode_produksi='BATCH-2026-08', sku_id=sku2.id, qty=150))

        # Distribusi
        db.add(DistribusiCutting(
            tanggal='2026-08-14', kode_produksi='BATCH-2026-08',
            person_id=penjahit.id, jenis='PENJAHIT', sku_id=sku1.id, qty=100,
        ))
        db.add(DistribusiCutting(
            tanggal='2026-08-14', kode_produksi='BATCH-2026-08',
            person_id=penjahit.id, jenis='PENJAHIT', sku_id=sku2.id, qty=80,
        ))
        db.add(DistribusiCutting(
            tanggal='2026-08-15', kode_produksi='BATCH-2026-08',
            person_id=pengsup.id, jenis='PENGSUP', sku_id=sku1.id, qty=50,
        ))
        db.add(DistribusiCutting(
            tanggal='2026-08-15', kode_produksi='BATCH-2026-08',
            person_id=pengsup.id, jenis='PENGSUP', sku_id=sku2.id, qty=40,
        ))

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
    for h in res.getheaders():
        if h[0].lower() == 'set-cookie':
            COOKIE = h[1].split(';')[0]
    conn.close()
    return res.status, json.loads(data) if data else {}


def api_post(path, body=None):
    global COOKIE
    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    headers = {"Content-Type": "application/json"}
    if COOKIE:
        headers["Cookie"] = COOKIE
    payload = json.dumps(body) if body else ""
    conn.request("POST", path, payload, headers)
    res = conn.getresponse()
    data = res.read().decode()
    for h in res.getheaders():
        if h[0].lower() == 'set-cookie':
            COOKIE = h[1].split(';')[0]
    conn.close()
    return res.status, json.loads(data) if data else {}


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

    status, _ = api_post("/api/auth/login", {"username": "admin", "password": "admin123"})
    check("Login", status == 200, f"status={status}")

    # ── Test 1: List batches ─────────────────────────────────────
    print("\n[TEST 1] List batches")
    status, data = api_get("/api/profit/batches")
    check("List batches 200", status == 200, f"status={status}")
    check("Has BATCH-2026-08", "BATCH-2026-08" in data.get("batches", []), f"got {data.get('batches')}")

    # ── Test 2: Analyze batch ────────────────────────────────────
    print("\n[TEST 2] Analyze batch")
    status, data = api_get("/api/profit/analyze/BATCH-2026-08")
    check("Analyze 200", status == 200, f"status={status}")
    check("kain_qty = 50", data.get("kain_qty") == 50, f"got {data.get('kain_qty')}")
    check("kain_total = 3,000,000", data.get("kain_total") == 3_000_000, f"got {data.get('kain_total')}")
    check("cut_qty = 350 (200+150)", data.get("cut_qty") == 350, f"got {data.get('cut_qty')}")
    check("dist_home = 180 (100+80)", data.get("dist_home") == 180, f"got {data.get('dist_home')}")
    check("dist_sup = 90 (50+40)", data.get("dist_sup") == 90, f"got {data.get('dist_sup')}")
    check("total_dist = 270", data.get("total_dist") == 270, f"got {data.get('total_dist')}")
    check("verif_status = TERTAHAN (270 < 350)", data.get("verif_status") == "TERTAHAN", f"got {data.get('verif_status')}")

    # Revenue: (100*85000 + 80*75000 + 50*85000 + 40*75000) = 8.5M + 6M + 4.25M + 3M = 21.75M
    expected_rev = 100*85000 + 80*75000 + 50*85000 + 40*75000
    check(f"total_revenue = {expected_rev}", data.get("total_revenue") == expected_rev, f"got {data.get('total_revenue')}")

    # ── Test 3: Toggle status ────────────────────────────────────
    print("\n[TEST 3] Toggle status")
    status, data = api_post("/api/profit/toggle-status/BATCH-2026-08")
    check("Toggle 200", status == 200, f"status={status}")
    check("new_status = SELESAI", data.get("new_status") == "SELESAI", f"got {data.get('new_status')}")

    # Verify
    status, data = api_get("/api/profit/analyze/BATCH-2026-08")
    check("status_kain = SELESAI after toggle", data.get("status_kain") == "SELESAI", f"got {data.get('status_kain')}")

    # Toggle back
    status, data = api_post("/api/profit/toggle-status/BATCH-2026-08")
    check("Toggle back to OPEN", data.get("new_status") == "OPEN", f"got {data.get('new_status')}")

    # ── Test 4: Save history ─────────────────────────────────────
    print("\n[TEST 4] Save profit history")
    status, data = api_post("/api/profit/save-history?kode_produksi=BATCH-2026-08")
    check("Save history 200", status == 200, f"status={status}")
    check("total_profit exists", "total_profit" in data, f"keys: {list(data.keys())}")

    # ── Test 5: List history ─────────────────────────────────────
    print("\n[TEST 5] List profit history")
    status, data = api_get("/api/profit/history")
    check("History 200", status == 200, f"status={status}")
    check("History has 1 record", isinstance(data, list) and len(data) == 1, f"got {len(data) if isinstance(data, list) else 'not list'}")

    # ── Test 6: Tarif CRUD ──────────────────────────────────────
    print("\n[TEST 6] Tarif CRUD")
    status, data = api_get("/api/profit/tarif")
    check("List tarif 200", status == 200, f"status={status}")
    check("Has 2 tarif", isinstance(data, list) and len(data) == 2, f"got {len(data) if isinstance(data, list) else 'not list'}")

    status, data = api_post("/api/profit/tarif", {"kode_sku": "NEW-SKU", "tarif_jahit": 500, "tarif_pengsup_potongan": 1200})
    check("Create tarif 200", status == 200, f"status={status}")

    status, data = api_get("/api/profit/tarif")
    check("Now has 3 tarif", isinstance(data, list) and len(data) == 3, f"got {len(data)}")

    # ── Summary ──────────────────────────────────────────────────
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
