"""
E2E Test: Payroll import endpoints.
"""
import sys, os, io, json, time, subprocess, http.client, http.cookiejar, urllib.request

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

# Login to get cookies
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
login_data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode()
req_login = urllib.request.Request(BASE + '/api/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
resp = opener.open(req_login)
print(f"Login: {resp.status}")

# Create persons
for nama, tipe in [('Budi', 'PENJAHIT'), ('Sari', 'SUPPLIER'), ('Andi', 'KARYAWAN'), ('Dedi', 'KARYAWAN')]:
    data = json.dumps({'nama': nama, 'person_type': tipe}).encode()
    r = urllib.request.Request(BASE + '/api/persons', data=data, headers={'Content-Type': 'application/json'})
    opener.open(r)

# Create SKU
for kode in ['SKU-A', 'SKU-B', 'SKU-C']:
    data = json.dumps({'kode_sku': kode, 'nama_produk': f'Produk {kode}', 'kategori': 'Test'}).encode()
    r = urllib.request.Request(BASE + '/api/sku', data=data, headers={'Content-Type': 'application/json'})
    opener.open(r)

print("Setup done.\n")

import urllib.request

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS: {name}")
    except AssertionError as e:
        failed += 1
        print(f"  FAIL: {name} -- {e}")
    except Exception as e:
        failed += 1
        print(f"  ERROR: {name} -- {e}")

def multipart_upload(path, filename, file_bytes, content_type):
    """Upload multipart file using cookie-aware opener."""
    boundary = '----TestBoundary'
    body_parts = []
    body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'.encode())
    body_parts.append(file_bytes)
    body_parts.append(f'\r\n--{boundary}--\r\n'.encode())
    body = b''.join(body_parts)

    req = urllib.request.Request(BASE + path, data=body, headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    })
    req.method = 'POST'
    resp = opener.open(req)
    return resp.status, json.loads(resp.read())

# ── Test 1: Import Excel Penjahit ──
print("=== TEST 1: Import Excel Penjahit ===")

from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.append(['SKU/Garapan', 'Qty', 'Harga/Tarif'])
ws.append(['Garapan A', 10, 5000])
ws.append(['Garapan B', 5, 8000])
ws.append(['Garapan C', 3, 12000])
buf = io.BytesIO()
wb.save(buf)
buf.seek(0)

s1, d1 = multipart_upload('/api/gaji/import-excel-penjahit', 'test.xlsx', buf.read(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

def test_import_penjahit():
    assert s1 == 200, f"Status {s1}: {d1}"
    assert d1['count'] == 3, f"Expected 3, got {d1['count']}"
    assert d1['items'][0]['nama_garapan'] == 'Garapan A'
    assert d1['items'][0]['total'] == 50000

test('Import Excel Penjahit', test_import_penjahit)

# ── Test 2: Import Excel Pengsup ──
print("\n=== TEST 2: Import Excel Pengsup ===")

wb2 = Workbook()
ws2 = wb2.active
ws2.title = "Daftar_Pemasukan"
ws2.append(["NAMA", "Budi"])
ws2.append(["TANGGAL", "2026-08-28"])
ws2.append(["KAIN_QTY", 10])
ws2.append(["KAIN_HARGA", 25000])
ws2.append(["BON_TAMBAH", 50000])
ws2.append(["BON_POTONG", 0])
ws2.append([])
ws2.append(["SKU/Nama", "Qty", "Harga/Tarif", "Tipe/Kategori"])
ws2.append(["Setor A", 20, 3000, "Setor Barang Jadi (Kain)"])
ws2.append(["Potong B", 15, 2000, "Jasa Potongan (Potongan)"])
buf2 = io.BytesIO()
wb2.save(buf2)
buf2.seek(0)

s2, d2 = multipart_upload('/api/gaji/import-excel-pengsup', 'pengsup.xlsx', buf2.read(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

def test_import_pengsup():
    assert s2 == 200, f"Status {s2}: {d2}"
    assert d2['count'] == 2, f"Expected 2, got {d2['count']}"
    assert d2['kain_qty'] == 10
    assert d2['kain_harga'] == 25000
    assert d2['tambah_bon'] == 50000

test('Import Excel Pengsup', test_import_pengsup)

# ── Test 3: Save Pasukan Batch ──
print("\n=== TEST 3: Save Pasukan Batch ===")

pasukan_data = {
    "tanggal_proses": "2026-08-28",
    "tarif_normal": 140,
    "tarif_lembur": 160,
    "karyawan": [
        {
            "person_id": 3, "nama": "Andi", "hadir": 5,
            "menit_normal": 2400, "tarif_normal": 140,
            "menit_lembur": 300, "tarif_lembur": 160,
            "gaji_kotor": 384000, "bon_lama": 0,
            "potong_bon": 0, "gaji_bersih": 384000,
            "daily_records": [
                {"tanggal": "23 Sen", "masuk": "08:00", "keluar": "17:00", "menit_normal": 480, "menit_lembur": 60},
                {"tanggal": "24 Sel", "masuk": "07:50", "keluar": "16:50", "menit_normal": 480, "menit_lembur": 50},
            ]
        },
        {
            "person_id": 4, "nama": "Dedi", "hadir": 3,
            "menit_normal": 1440, "tarif_normal": 140,
            "menit_lembur": 0, "tarif_lembur": 160,
            "gaji_kotor": 201600, "bon_lama": 0,
            "potong_bon": 0, "gaji_bersih": 201600,
            "daily_records": []
        },
    ]
}

data3 = json.dumps(pasukan_data).encode()
req3 = urllib.request.Request(BASE + '/api/gaji/save-pasukan', data=data3, headers={'Content-Type': 'application/json'})
req3.method = 'POST'
resp3 = opener.open(req3)
d3 = json.loads(resp3.read())

def test_save_pasukan():
    assert resp3.status == 200, f"Status {resp3.status}"
    assert d3['saved'] == 2, f"Expected 2 saved, got {d3['saved']}"

test('Save Pasukan Batch', test_save_pasukan)

# ── Test 4: Verify Salary Runs Created ──
print("\n=== TEST 4: Verify Salary Runs ===")

req4 = urllib.request.Request(BASE + '/api/gaji?tipe=PASUKAN_KARYAWAN')
resp4 = opener.open(req4)
d4 = json.loads(resp4.read())

def test_salary_runs():
    assert len(d4) == 2, f"Expected 2 runs, got {len(d4)}"
    andi = next(r for r in d4 if r['person_nama'] == 'Andi')
    assert andi['gaji_kotor'] == 384000, f"Andi gaji_kotor: {andi['gaji_kotor']}"
    assert andi['gaji_bersih'] == 384000

test('Salary Runs Created', test_salary_runs)

# ── Test 5: Edit Karyawan ──
print("\n=== TEST 5: Edit Karyawan ===")
# 08:00→17:30 = 570 min → normal=480, lembur=90
# 07:50→Lupa = 0 min

edit_data = {
    "person_id": 3,
    "tarif_normal": 150,
    "tarif_lembur": 170,
    "potong_bon": 0,
    "daily_records": [
        {"tanggal": "23 Sen", "tap_masuk": "08:00", "tap_keluar": "17:30", "menit_normal": 0, "menit_lembur": 0},
        {"tanggal": "24 Sel", "tap_masuk": "07:50", "tap_keluar": "Lupa", "menit_normal": 0, "menit_lembur": 0},
    ]
}

data5 = json.dumps(edit_data).encode()
req5 = urllib.request.Request(BASE + '/api/gaji/edit-karyawan', data=data5, headers={'Content-Type': 'application/json'})
req5.method = 'POST'
resp5 = opener.open(req5)
d5 = json.loads(resp5.read())

def test_edit_karyawan():
    assert resp5.status == 200, f"Status {resp5.status}"
    assert d5['menit_normal'] == 480, f"Normal: {d5['menit_normal']}"
    assert d5['menit_lembur'] == 90, f"Lembur: {d5['menit_lembur']}"
    assert d5['gaji_kotor'] == 480*150 + 90*170, f"Gaji kotor: {d5['gaji_kotor']}"

test('Edit Karyawan', test_edit_karyawan)

# ── Test 6: Create Gaji Penjahit ──
print("\n=== TEST 6: Create Gaji Penjahit ===")

gaji_penjahit = {
    "tipe": "BORONGAN_PENJAHIT",
    "person_id": 1,
    "tanggal_proses": "2026-08-28",
    "tambah_bon": 0,
    "potong_bon": 0,
    "line_items": [
        {"model_code": "Garapan A", "qty": 10, "tarif_per_pcs": 5000},
        {"model_code": "Garapan B", "qty": 5, "tarif_per_pcs": 8000},
    ]
}

req6 = urllib.request.Request(BASE + '/api/gaji', data=json.dumps(gaji_penjahit).encode(), headers={'Content-Type': 'application/json'})
req6.method = 'POST'
resp6 = opener.open(req6)
d6 = json.loads(resp6.read())

def test_create_penjahit():
    assert resp6.status == 200, f"Status {resp6.status}"
    assert d6['gaji_kotor'] == 90000, f"Gaji kotor: {d6['gaji_kotor']}"

test('Create Gaji Penjahit', test_create_penjahit)

# ── Test 7: Get Attendance Records ──
print("\n=== TEST 7: Get Attendance Records ===")

# Find Andi's run
andi_run = next(r for r in d4 if r['person_nama'] == 'Andi')
req7 = urllib.request.Request(BASE + f'/api/gaji/attendance/{andi_run["id"]}')
resp7 = opener.open(req7)
d7 = json.loads(resp7.read())

def test_attendance():
    assert len(d7) == 2, f"Expected 2 records, got {len(d7)}"

test('Get Attendance Records', test_attendance)

# Cleanup
proc.terminate()
try: proc.wait(timeout=3)
except: proc.kill()

print(f"\n{'='*50}")
print(f"RESULTS: {passed} passed, {failed} failed")
print(f"{'='*50}")

if failed > 0:
    sys.exit(1)
