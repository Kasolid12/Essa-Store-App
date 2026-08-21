# 📘 PANDUAN MIGRASI DATABASE KE CLOUD — YAZMINA HIJAB

> **Dokumen pedoman kerja** untuk memindahkan penyimpanan data YAZMINA HIJAB dari SQLite lokal ke arsitektur **hybrid (SQLite lokal + PostgreSQL cloud)**, dengan aplikasi tetap berjalan sepenuhnya offline di komputer lokal.

| | |
|---|---|
| **Status dokumen** | ✅ Disetujui sebagai pedoman (v1.1) |
| **Status implementasi** | ✅ **Fase 0–7 SELESAI** (setup Neon, refactor koneksi, skema cloud, seed, push/pull dua arah, `updated_at` aktif, **ID mapping + last-write-wins + delete dua arah + kepemilikan perangkat + tombol sync manual & indikator status**) |
| **Tanggal** | 5 Agustus 2026 |
| **Keputusan cloud DB** | **Neon (PostgreSQL serverless, free tier)** |
| **Arsitektur** | Hybrid: SQLite = database kerja, Neon = backup + sinkronisasi |

---

## 1. Ringkasan Eksekutif

**Kebutuhan yang disepakati bersama:**
1. ✅ Backup & keamanan data (data aman di cloud walau laptop rusak)
2. ✅ Akses multi-perangkat (beberapa komputer bisa memakai data yang sama)
3. ✅ **WAJIB tetap berfungsi penuh saat internet mati** (operasional toko tidak boleh berhenti)

**Konsekuensi arsitektur:** karena wajib offline, aplikasi TIDAK boleh bergantung penuh ke database cloud. Solusinya:

```
┌─ PC Lokal (pemakai utama) ──────────┐      ┌─ Neon Cloud (PostgreSQL) ────────┐
│  essa.db (SQLite)                    │ sync │  Database cloud (free tier)       │
│  • Database kerja sehari-hari        │ ───► │  • Salinan data (backup)          │
│  • Offline-first, 100% tanpa internet│ ◄─── │  • Pusat data multi-perangkat     │
│  • Cepat, tanpa latency              │      │  • Dapat diakses perangkat lain    │
└──────────────────────────────────────┘      └───────────────────────────────────┘
```

**Prinsip yang tidak boleh dilanggar:**
- Aplikasi desktop berjalan identik seperti sekarang (tidak butuh internet untuk dipakai).
- Cloud adalah **lapisan sinkronisasi & backup**, bukan pengganti database kerja.
- Semua perubahan harus bisa di-rollback (data lokal selalu ada).

---

## 2. Inventaris Database Saat Ini

### 2.1 Teknologi

| Komponen | Nilai |
|---|---|
| ORM | SQLAlchemy 2.0 (tipe modern `Mapped` / `mapped_column`) |
| Database | SQLite file tunggal `essa.db` di root proyek |
| Migration | Alembic — folder aktif `data/migrations/` (sesuai `alembic.ini`) |
| Session | `scoped_session` dari `data/database.py` |
| Aplikasi | PySide6 desktop, `main.py` memanggil `Base.metadata.create_all()` saat start |

> ⚠️ Catatan: folder `migrations/` (root) yang tercantum di dokumentasi lama **sudah tidak ada**. Satu-satunya jalur migrasi yang benar adalah `data/migrations/`.

### 2.2 Daftar 26 Tabel (grup fungsi)

| Grup | Tabel | Keterangan |
|---|---|---|
| **Master** | `sku_master` | Katalog produk; self-reference `parent_sku_id` (parent → variants) |
| | `persons` | KARYAWAN / PENJAHIT / PENGSUP / KLIEN / SUPPLIER; kolom generated `nama_uppercase` |
| | `clients` | Klien (pengganti Person bertipe KLIEN) |
| | `garapan_rates` | Tarif per pcs per model SKU |
| | `tarif_master` | Tarif jahit / pengsup kain / potongan per `kode_sku` |
| | `master_tarif_penjahit` | Tarif dropdown payroll penjahit (`kode_garapan` unik) |
| | `app_settings` | Key-value pengaturan |
| **Catatan Harian** | `hasil_cutting` | Hasil cutting (FK → `sku_master`, `debt_entries`) |
| | `distribusi_cutting` | Distribusi cutting ke penjahit/pengsup (FK → `persons`, `sku_master`, `hasil_cutting`) |
| | `modal_operasional` | Pengeluaran operasional |
| | `pengeluaran_offline` | Penjualan offline (FK → `sku_master`, `persons`, `clients`) |
| **Hutang** | `debt_entries` | Hutang BARANG / MODAL (FK → `persons`, `sku_master`) |
| | `debt_payments` | Pembayaran hutang (FK → `debt_entries`) |
| **Bon** | `bon_balances` | Saldo bon per person (FK → `persons`, unik per person) |
| | `bon_movements` | Riwayat tambah/potong bon (FK → `persons`) |
| **Payroll** | `salary_runs` | Run gaji borongan/pengsup/pasukan (FK → `persons`) |
| | `salary_line_items` | Detail line gaji (FK → `salary_runs`, `sku_master`, `master_tarif_penjahit`) |
| | `pengsup_reconciliation` | Rekonsiliasi pengsup (FK → `salary_runs`, `sku_master`) |
| | `attendance_records` | Absensi harian karyawan (FK → `salary_runs`, `persons`) |
| **Invoice** | `invoices` | Invoice (FK → `persons`; `nomor_invoice` unik) |
| | `invoice_lines` | Detail item invoice (FK → `invoices`, `sku_master`) |
| | `client_receivables` | Piutang (FK → `invoices`, `persons` legacy, `clients`) |
| | `client_receivable_payments` | Pembayaran piutang (FK → `client_receivables`) |
| **Stok & Audit** | `stock_movements` | Mutasi stok (FK → `sku_master`) |
| | `audit_log` | Log audit semua tabel |
| **Profit** | `profit_history` | Riwayat perhitungan profit (FK → `debt_entries`) |

**Total: 26 tabel, semuanya relasional (foreign key).**

### 2.3 Pola Umum di Seluruh Model

1. **Soft-delete**: hampir semua tabel punya kolom `is_deleted` (0/1); semua query di view memfilter `is_deleted == 0`.
2. **Timestamp**: `created_at` + `updated_at` dengan `datetime.now` (semua 26 tabel punya `updated_at` sejak Fase 6.1).
3. **Status uppercase string**: `OPEN` / `PARTIAL` / `LUNAS` / `SELESAI`.
4. **Query 100% lewat ORM**: `dashboard_queries.py` dan semua view memakai `session.query(...)` / `func.sum()` — **tidak ada SQL mentah di jalur aplikasi** (kecuali di file migration). Ini membuat aplikasi portabel antar-dialek database.

### 2.4 Daftar File Titik Sentuh Database

| File | Peran |
|---|---|
| `data/database.py` | Engine + session factory (satu-satunya pembuat koneksi) |
| `data/models/*.py` | 14 file model ORM |
| `data/migrations/versions/*.py` | 5 file migration Alembic |
| `utils/backup_engine.py` | Backup otomatis saat aplikasi ditutup |
| `data/excel_importer.py` | Import SKU/tarif dari Excel (lewat ORM — aman) |
| `data/dashboard_queries.py` | Query agregat dashboard (lewat ORM — aman) |
| `ui/views/*.py` | Semua view (lewat ORM — aman) |

---

## 3. Hambatan SQLite-Spesifik yang Harus Diperbaiki

Hasil audit menyeluruh. Ini satu-satunya titik yang menghalangi jalannya di PostgreSQL.

| # | Lokasi | Masalah SQLite-spesifik | Dampak di Postgres |
|---|---|---|---|
| 1 | `data/database.py:9` | `DATABASE_URL = "sqlite:///..."` hardcoded | Tidak bisa dialihkan ke cloud tanpa edit kode |
| 2 | `data/database.py:16-19` | Event `PRAGMA journal_mode=WAL` dijalankan di setiap koneksi | **Error** — `PRAGMA` tidak dikenal Postgres |
| 3 | `data/models/person.py:19` | `Computed("UPPER(nama)")` (GENERATED ALWAYS) | Aman di Postgres 12+ (didukung), tapi **wajib diuji** |
| 4 | `data/migrations/versions/d8e3f4a5b6c7:71` | `SELECT last_insert_rowid()` | **Error** — fungsi tidak ada di Postgres |
| 5 | `data/migrations/versions/d8e3f4a5b6c7:69` | `datetime('now')` dalam SQL mentah | **Error** — fungsi SQLite, di Postgres pakai `now()`/param Python |
| 6 | `utils/backup_engine.py` | Backup via modul `sqlite3` + path file | Hanya bisa backup file SQLite lokal; perlu strategi backup cloud baru |
| 7 | Migration `c9b50081130a` (initial) | Skema dibuat sekali jalan — tidak bermasalah, hanya perlu diverifikasi jalannya di Postgres | — |

> Catatan penting: item 4–5 terjadi di migration yang **sudah ter-apply** di SQLite lokal. Perbaikan hanya dibutuhkan agar chain migration bisa dijalankan dari nol di Postgres (cloud). Perbaikan tidak mengubah data SQLite yang sudah ada.

---

## 4. Keputusan Layanan Cloud (Hasil Riset & Perbandingan)

| Opsi | Free tier | Koneksi langsung dari desktop app | Kesesuaian dengan SQLAlchemy relasional | Keputusan |
|---|---|---|---|---|
| **Neon (PostgreSQL serverless)** ✅ | 0.5 GB storage + 100 compute jam/bulan | ✅ TCP langsung (`postgresql://...`) | ✅ Sempurna — tetap SQL + ORM + Alembic | **PILIHAN** |
| Supabase (Postgres) | Free, tapi project **di-pause** setelah ~1 minggu idle | ⚠️ Harus lewat pooler pgbouncer (bisa bermasalah dgn transaksi) | ✅ | Alternatif cadangan |
| Firebase (Firestore) | Free tier | — (API HTTP/NoSQL) | ❌ **Tidak cocok** — NoSQL, butuh tulis ulang seluruh aplikasi | ❌ Ditolak |
| Turso / Cloudflare D1 (SQLite cloud) | Free | — (driver libSQL) | ⚠️ Driver berbeda, `backup_engine.py` ikut rusak | ❌ Ditolak |

**Keputusan: NEON.** Alasan:
1. Postgres murni — migration Alembic, ORM, dan relasi berjalan hampir tanpa perubahan.
2. Free tier cukup untuk data operasional toko (0.5 GB jauh di atas kebutuhan).
3. Koneksi TCP standar langsung dari Python desktop app (driver `psycopg2`).
4. Auto-suspend saat tidak dipakai + auto-resume otomatis saat dipanggil → biaya 0.
5. Tidak perlu pooler seperti Supabase.

**Detail free tier Neon:**
- Storage: 0.5 GB (data aplikasi toko kecil, sangat cukup)
- Compute: 100 jam/bulan (sinkronisasi beberapa kali sehari pakai < 2 jam/bulan)
- Auto-suspend: ±5 menit idle (bisa diatur)
- Format URL: `postgresql://<user>:<password>@<host>/<dbname>?sslmode=require`

---

## 5. Rencana Implementasi Bertahap

> Setiap fase punya: **Langkah → Verifikasi → Kriteria selesai**. Jangan lanjut ke fase berikutnya sebelum kriteria selesai terpenuhi.

---

### FASE 0 — Setup Akun Neon & Dapatkan Kredensial

**Langkah:**
1. Buka halaman setup Neon (tombol di percakapan / https://console.neon.tech).
2. Daftar (email/Google) → buat project baru (nama: `yazmina-hijab-cloud`).
3. Salin **connection string** dari *Connection Details*:
   ```
   postgresql://yazmina_owner:<password>@ep-xxxx.region.aws.neon.tech/yazmina_hijab?sslmode=require
   ```
4. Simpan string ini sebagai **`CLOUD_DATABASE_URL`** (belum dipakai kode, cukup simpan di password manager dulu).
5. **Penyempurnaan desain (v1.1):** koneksi cloud dipisah ke `CLOUD_DATABASE_URL`, sedangkan aplikasi selalu memakai SQLite lokal (`APP_DATABASE_URL`, default `essa.db`). Alasan: aplikasi **wajib offline** — cloud tidak boleh mengendalikan jalur utama aplikasi. Engine cloud hanya dibuat oleh skrip sinkronisasi/migrasi (`data/database.py` → `get_cloud_engine()`).

**Verifikasi:**
- Bisa connect dari laptop: `psql "<DATABASE_URL>" -c "SELECT 1;"` (atau via UI console Neon).

**Kriteria selesai:** ✅ `DATABASE_URL` valid dan bisa dikoneksi dari laptop.

---

### FASE 1 — Refactor Lapisan Database (`data/database.py` + `.env`)

Tujuan: koneksi menjadi **dialect-agnostik** — otomatis pakai Postgres bila `DATABASE_URL` diisi, fallback ke SQLite lokal bila kosong.

**Langkah:**
1. Buat file `.env` di root proyek (TIDAK boleh di-commit — tambahkan ke `.gitignore`):
   ```ini
   # Aplikasi SELALU memakai SQLite lokal — jangan isi kecuali uji coba:
   # APP_DATABASE_URL=sqlite:///essa.db

   # Cloud HANYA untuk skrip sinkronisasi & migrasi:
   CLOUD_DATABASE_URL=postgresql+psycopg2://yazmina_owner:<password>@ep-xxxx.region.aws.neon.tech/yazmina_hijab?sslmode=require
   ```
2. Tambahkan `python-dotenv` dan `psycopg2-binary` ke `requirements.txt`.
3. Ganti isi `data/database.py`:```python
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv

load_dotenv()  # baca .env bila ada

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ENGINE APLIKASI — WAJIB SQLite lokal (offline-first)
DATABASE_URL = os.environ.get(
    "APP_DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'essa.db')}",
)
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# PRAGMA HANYA untuk SQLite — error jika dijalankan di Postgres
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = scoped_session(session_factory)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── ENGINE CLOUD (Neon) — HANYA untuk sinkronisasi/migrasi ──
# (URL dibaca lazy dari env CLOUD_DATABASE_URL — lihat data/database.py)
_cloud_engine = None

def get_cloud_engine():
    global _cloud_engine
    url = os.environ.get("CLOUD_DATABASE_URL", "").strip()
    if not url:
        return None
    if _cloud_engine is None:
        _cloud_engine = create_engine(url, echo=False, pool_pre_ping=True)
    return _cloud_engine

def get_cloud_session():
    eng = get_cloud_engine()
    if eng is None:
        raise RuntimeError("CLOUD_DATABASE_URL belum diatur di file .env")
    Session = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return Session()
```

**Verifikasi:**
- Jalankan aplikasi `python main.py` tanpa `.env` → semua menu normal (SQLite).
- Test koneksi cloud terpisah (bukan di aplikasi): `python -c "from data.database import engine; print(engine.url)"`.

**Kriteria selesai:** ✅ Aplikasi jalan identik di SQLite; engine siap pakai untuk dua dialek.

---

### FASE 2 — Perbaikan Migration Agar Dialect-Agnostik

Tujuan: chain migration bisa dijalankan dari nol di Postgres tanpa error SQLite-spesifik.

**Langkah (file `data/migrations/versions/d8e3f4a5b6c7_add_clients_table.py`):**

1. Ganti `datetime('now')` → bind parameter `datetime` Python:
   ```python
   from datetime import datetime
   ...
   result = connection.execute(
       sa.text("""
           INSERT INTO clients (nama, alamat, no_hp, catatan, is_active, is_deleted, created_at, updated_at)
           VALUES (:nama, :alamat, :no_hp, :catatan, 1, 0, :now, :now)
       """),
       {"nama": p.nama, "alamat": p.alamat, "no_hp": p.no_hp,
        "catatan": p.catatan, "now": datetime.now()},
   )
   ```
2. Ganti `SELECT last_insert_rowid()` → primary key dari hasil insert (SQLAlchemy otomatis memakai `lastrowid` di SQLite dan `RETURNING` di Postgres):
   ```python
   client_id = result.inserted_primary_key[0]
   ```
3. Audit file migration lain:
   - `e4fc4d7866da_make_client_receivables_person_id_.py` → verifikasi tidak ada `last_insert_rowid` / `datetime('now')` / batch mode yang gagal di Postgres.
   - `b7e1a2c3d4f5_add_profit_history.py` → hanya CREATE TABLE, seharusnya aman.

**Verifikasi:**
- Jalankan migration terhadap **Postgres kosong** (lihat Fase 3).

**Kriteria selesai:** ✅ `alembic upgrade head` berhasil penuh di Postgres tanpa error.

---

### FASE 3 — Buat Skema di Cloud (Postgres)

> ⚠️ **Temuan audit skema (5 Agu 2026):** DB live (`essa.db`) TIDAK bisa dibuat ulang
> 100% oleh migration Alembic. Kolom ini ada di DB live tapi TIDAK ada di migration:
> `hasil_cutting.kode_produksi`, `hasil_cutting.modal_hutang_id`, `distribusi_cutting.kode_produksi`,
> `distribusi_cutting.hasil_cutting_id`, `debt_entries.kode_produksi`, `debt_entries.status_cutting`,
> `salary_line_items.tarif_id` (DB live dibangun lewat `create_all` dari model yang sudah berevolusi).
> Karena itu skema cloud DIBUAT LANGSUNG DARI MODEL (sama seperti cara DB live dibangun),
> bukan dari migration. Alembic tetap dipakai untuk migrasi schema di masa depan.

**Langkah:**
1. Pastikan Fase 1 & 2 selesai dan `CLOUD_DATABASE_URL` terisi di `.env`.
2. Jalankan skrip pembuat skema dari model (sekali saja):
   ```bash
   set -a; source .env; set +a
   python scripts/create_cloud_schema.py
   ```
3. Tandai versi alembic agar migrasi berikutnya berjalan normal (pastikan env cloud termuat):
   ```bash
   set -a; source .env; set +a
   alembic stamp head
   ```
4. Verifikasi jumlah tabel:
   ```bash
   psql "$CLOUD_DATABASE_URL" -c "\dt"
   ```

**Verifikasi:**
- 26 tabel muncul di cloud + tabel `alembic_version` berisi `e4fc4d7866da`.
- Kolom drift (kode_produksi, tarif_id, dll.) ikut terbentuk — cek di console Neon.

**Kriteria selesai:** ✅ Skema cloud identik dengan ekspektasi model aplikasi.

---

### FASE 4 — Seed Data Awal (SQLite → Neon, satu kali)

Tujuan: mengisi cloud dengan seluruh data `essa.db` yang sudah ada.

**Langkah — buat skrip `scripts/seed_cloud.py`:**
1. Buka dua session: `SessionLocal` (SQLite lokal) dan engine cloud (import `DATABASE_URL` dari env).
2. Salin data **urutan aman terhadap foreign key** (induk dulu, lalu anak):
   ```
   sku_master → persons → clients → garapan_rates → tarif_master → master_tarif_penjahit
   → app_settings → debt_entries → debt_payments → hasil_cutting → distribusi_cutting
   → modal_operasional → pengeluaran_offline → bon_balances → bon_movements
   → salary_runs → salary_line_items → pengsup_reconciliation → attendance_records
   → invoices → invoice_lines → client_receivables → client_receivable_payments
   → stock_movements → audit_log → profit_history
   ```
3. **Pertahankan ID asli** saat insert (tulis `id` eksplisit). Ini membuat relasi FK antar-baris tetap benar dan menyederhanakan sinkronisasi berikutnya.
4. Tampilkan statistik: tabel → jumlah baris yang disalin + jumlah baris yang gagal.

**Verifikasi:**
- Jumlah baris per tabel sama persis antara SQLite dan cloud.
- Query silang teruji: ambil 1 invoice + lines-nya di cloud, cocokkan dengan lokal.

**Kriteria selesai:** ✅ Cloud berisi snapshot data identik dengan lokal (one-time initial sync).

---

### FASE 5 — Backup Engine Diperluas (Sinkronisasi Satu Arah: Lokal → Cloud) ✅ SELESAI

Tujuan: **setiap perubahan di lokal otomatis ter-backup ke cloud** (one-way). Perangkat lain bisa membaca data cloud.

**Implementasi (5 Agu 2026) — `utils/cloud_sync.py`, metode DIFF-SYNC per primary key:**
1. Untuk setiap tabel (urutan induk→anak): baca semua baris lokal & cloud, bandingkan per id.
   - Baris lokal yang belum ada di cloud → **INSERT** (`ON CONFLICT DO UPDATE`).
   - Baris yang nilainya berbeda → **UPDATE**.
   - Baris cloud yang sudah tidak ada di lokal → **DELETE** (urutan anak→induk; cloud = cermin lokal).
2. **Tidak butuh kolom `updated_at`** — diff langsung membandingkan nilai (mayoritas tabel belum punya `updated_at`, jadi pendekatan ini lebih andal).
3. **Normalisasi nilai**: datetime/date dibandingkan dalam bentuk string agar konsisten lintas dialek; kolom computed (`persons.nama_uppercase`) tidak pernah ditulis (Postgres mengisinya otomatis).
4. **Normalisasi FK**: nilai FK yang menunjuk id tidak ada (mis. `parent_sku_id=0`) → `NULL`, baik saat perbandingan maupun penulisan — hasilnya diff stabil (tidak re-sync terus-menerus) dan tidak melanggar constraint Postgres.
5. **Pemicu**: otomatis di `closeEvent` `main.py` (setelah `backup_database()`); manual via `python -m utils.cloud_sync`.
6. **Pengaman**: fungsi tidak pernah melempar exception (aman saat app ditutup); bila total baris lokal = 0 (kemungkinan lokasi DB salah), penghapusan di cloud dibatalkan agar backup tidak ikut terhapus; `connect_timeout=5s` pada cloud engine agar penutupan app tidak menggantung.
7. **Waktu sinkronisasi terakhir** disimpan di `app_settings` (key `cloud_last_sync`) dan ikut tersinkron — pengganti tabel meta `sync_state`.
8. **Kinerja**: saat compute Neon hangat, sync ±3 detik; saat dingin (auto-suspend setelah ±5 menit idle) bisa ±25 detik. Tips: naikkan *suspend delay* (mis. 1 jam) di pengaturan Neon agar penutupan aplikasi selalu cepat, atau jalankan `python -m utils.cloud_sync` manual di luar jam kerja.

**Verifikasi:**
- [x] Sync dijalankan → semua perbedaan terselesaikan (normalisasi datetime & kolom qty); run berikutnya hanya heartbeat `cloud_last_sync` (1 update) — **stabil/idempoten**.
- [x] Nilai pecahan `qty=50.25` tersalin utuh ke cloud (kolom diubah ke DOUBLE PRECISION).
- [ ] Ubah 1 data di aplikasi → tutup → buka cloud di console Neon: baris ter-update.

**Kriteria selesai:** ✅ Data lokal tersinkron ke cloud setiap kali aplikasi ditutup tanpa mengubah satu pun view.

---

### FASE 5.5 — Sinkronisasi Dua Arah Aman (PULL: Cloud → Lokal) ✅ SELESAI

Tujuan: perangkat baru (baru install) bisa **mendapatkan seluruh data dari cloud**, dan perangkat dengan file DB lama bisa **menggabungkan data cloud** — tanpa risiko menghapus data.

**Keputusan aturan konflik (6 Agu 2026): "perangkat yang sedang dipakai menang".**
- **PUSH** (lokal → cloud): nilai lokal selalu dikirim ke cloud (lokal menang).
- **PULL setup** (cloud → lokal, DB lokal KOSONG): unduh penuh — cloud menang (tidak ada data lokal).
- **PULL merge** (cloud → lokal, DB lokal BERISI): tambahkan baris cloud yang belum ada di lokal + perbarui baris yang nilainya berbeda (cloud menang), **TIDAK PERNAH menghapus data lokal**.
- Praktis: konflik nyata (2 perangkat mengedit baris yang sama) tidak terjadi karena umumnya hanya 1 perangkat yang menulis; kolom `updated_at` disiapkan agar Fase 6 bisa menerapkan *last-write-wins*.

**Implementasi (6 Agu 2026):**
1. `pull_from_cloud(mode)` di `utils/cloud_sync.py` — arah cloud → lokal dengan mode `setup` / `merge` / `auto`, memakai logika diff yang sama dengan push (per primary key, normalisasi datetime & FK, kolom computed dikecualikan, sanitasi FK dangling → NULL).
2. **Auto-pull perangkat baru**: di `main.py` saat start — bila `essa.db` lokal KOSONG dan `CLOUD_DATABASE_URL` tersedia, seluruh data cloud diunduh otomatis (sekali; setelah ada data, tidak diulang). Gagal/offline → dilewati tanpa memblokir aplikasi.
3. Manual: `python -m utils.cloud_sync --pull` (auto), `--pull setup` (lokal harus kosong), `--pull merge` (gabung, tidak menghapus lokal).
4. **Identitas perangkat**: `app_settings.device_id` (UUID 8 karakter) dibuat per perangkat dan TIDAK tertimpa id perangkat lain saat pull (fondasi `sync_state` Fase 6).
5. **Pengaman push multi-perangkat**: pass DELETE dilewati bila data lokal tampak parsial/stale (id cloud yang hilang di lokal > 25% dan ≥ 5 baris) — mencegah perangkat dengan DB lama menghapus data perangkat lain dari cloud.
6. **Fondasi Fase 6**: migration `a1b2c3d4e5f6` menambahkan kolom `updated_at` (nullable) ke 21 tabel yang belum punya — diterapkan ke cloud (`alembic upgrade head`). ✅ **Fase 6 (jalur tulis)**: model & migration kini juga diterapkan ke `essa.db` lokal, dan aplikasi mengisi kolom ini otomatis pada setiap insert/update.

> ✅ **Sejak Fase 6.2, mode `--pull` apa pun menjalankan sinkronisasi DUA ARAH penuh
> (tarik + kirim) dengan resolusi *last-write-wins* via `updated_at`** — bukan lagi
> "cloud menang mentah-mentah". Detail di bagian Fase 6.

**Verifikasi (6 Agu 2026):**
- [x] Setup pull ke DB SQLite temp: unduh penuh (~3,8 ribu baris); re-run ditolak (lokal berisi data).
- [x] Merge idempoten (0/0); merge mengembalikan baris yang dihapus lokal (insert=1).
- [x] `device_id` perangkat temp ≠ `device_id` cloud (identitas lokal tidak tertimpa).
- [x] Push regresi dari `essa.db` asli tetap OK dengan skema cloud baru (kolom `updated_at` dikecualikan dari sync).
- [ ] Perangkat baru nyata: install + salin `.env` + buka aplikasi → data muncul di dashboard.

**Kriteria selesai:** ✅ Perangkat baru dapat memperoleh data dari cloud tanpa menyalin `essa.db`.

---

### FASE 6 — Sinkronisasi Dua Arah Penuh (Multi-Perangkat) ✅ SELESAI (6 Agu 2026)

> **Status — bagian 1 (jalur tulis `updated_at`) & bagian 2 (ID mapping + LWW) SELESAI.**
> 1. ✅ Ke-21 model punya kolom `updated_at` (nullable, `default` + `onupdate=datetime.now`)
>    — semua tulis ORM mengisinya otomatis; migration `a1b2c3d4e5f6` diterapkan di
>    cloud **dan** `essa.db` lokal.
> 2. ✅ **Lapisan ID mapping** (`sync_id_map` lokal) — lihat di bawah.
> 3. ✅ **Last-write-wins** via `updated_at` (NULL dianggap paling lama) — lihat di bawah.
> 4. ✅ **Delete dua arah** berbasis pemetaan + tombstone.
>
> ⚠️ **Catatan zona waktu (dari review):** `updated_at` memakai waktu lokal perangkat
> (`datetime.now`). Untuk toko dalam satu zona waktu tidak masalah; bila perangkat
> tersebar di zona waktu berbeda, pertimbangkan memakai UTC (backfill + ubah model).

Tujuan: perangkat kedua bisa memakai & menulis data yang sama dengan aman.

**Lapisan ID mapping — tabel lokal `sync_id_map` (TIDAK pernah disinkronkan):**
- Kolom: `(table_name, local_id) → cloud_id, deleted_at (tombstone), last_seen`.
- Baris baru lokal dengan id bebas di cloud → memakai **id sama** (identity).
- Baris baru lokal yang id-nya sudah dipakai baris lain di cloud → diberi **id cloud BARU**
  (via sequence Postgres / MAX+1 yang aman per-run), pemetaan dicatat.
- **FK antar tabel diterjemahkan** lewat pemetaan (induk diproses lebih dulu) — anak
  selalu menunjuk id yang benar di cloud maupun lokal.
- Saat perangkat baru mengunduh data, id cloud dipakai apa adanya bila bebas, atau
  diberi id lokal baru bila bertabrakan (pemetaan dicatat dua arah).

**Last-write-wins (via `updated_at`):**
- NULL dianggap paling lama. Timestamp dibandingkan sebagai string kanonik
  `YYYY-MM-DD HH:MM:SS.ffffff` (konsisten lintas SQLite/Postgres).
- `updated_at` sama & nilai berbeda → "perangkat yang sedang dipakai menang" (lokal push).
- Baris yang isinya sama (selain `updated_at`) dianggap baris yang sama.

**Delete dua arah (berbasis pemetaan + tombstone):**
- Perangkat HANYA menghapus baris cloud yang ADA pemetaannya → baris milik perangkat
  lain yang belum pernah ditarik tidak akan ikut terhapus.
- Baris lokal yang dihapus: mapping diberi tombstone `deleted_at`; baris cloud ikut
  dihapus **kecuali** cloud sudah berubah setelah sync terakhir (edit perangkat lain
  menang, tombstone ditahan).
- Baris cloud yang dihapus perangkat lain: baris lokal dicerminkan (dihapus) **kecuali**
  perangkat ini mengeditnya setelah sync terakhir (edit lokal menang → di-cloud
  "dihidupkan kembali").

**Resiliensi konflik index unik (mis. `kode_sku` duplikat antar perangkat):**
- Konflik index unik pada baris tertentu **dilewati per-baris** (savepoint) dengan
  peringatan di console — tidak menggagalkan seluruh sinkronisasi. Baris itu tetap
  ada di sisinya dan dicoba lagi di sync berikutnya; selesaikan duplikat bisnisnya
  (rename/hapus) agar barisnya ikut tersinkron.

**Pemicu sinkronisasi dua arah penuh:**
- Otomatis saat aplikasi **dibuka** (thread latar, tidak memblokir window) dan saat
  aplikasi **ditutup** (`closeEvent`).
- Manual: `python -m utils.cloud_sync` (dua arah), `--pull setup` (perangkat baru),
  `--pull merge` (gabung).

**Hasil uji E2E (2 perangkat + cloud tiruan SQLite, `scripts/_test_twoway.py`):**
- [x] Tabrakan id: data perangkat B diberi id cloud baru, data A tidak tertimpa.
- [x] FK tertranslasi utuh (tanpa pelanggaran FK di cloud).
- [x] Last-write-wins: edit terbaru menang di semua perangkat.
- [x] Delete dua arah: baris yang dihapus di A hilang dari cloud & perangkat B.
- [x] Konvergen/idempoten: run kedua selalu 0 perubahan.
- [x] Regresi `essa.db` asli: 3.865 baris ter-backfill identity; sync 0 perubahan; count lokal = cloud (ALL MATCH).

**Kriteria selesai:** ✅ 2 perangkat: B menarik data A; perubahan B (baru/ubah/hapus) terlihat di A dan sebaliknya.

---

### FASE 6.3 — Kepemilikan Baris Antar Perangkat (`created_by_device` / `updated_by_device`) ✅ SELESAI (7 Agu 2026)

Tujuan: menggantikan heuristik backfill (perbandingan isi) saat perangkat standalone bergabung dengan **kepemilikan baris yang PASTI** — setiap baris tahu perangkat pembuat dan perangkat yang terakhir mengeditnya.

**Kolom (nullable TEXT) di SEMUA 26 tabel — migration `f6e5d4c3b2a1` (diterapkan ke cloud & `essa.db` lokal):**
- `created_by_device`: diisi OTOMATIS saat INSERT lewat event ORM di `data/models/base.py` (`CURRENT_DEVICE_ID` di-set `main.py` saat start dan oleh `utils/cloud_sync.py`) dengan `device_id` perangkat pembuat. **NULL = baris lama** (dibuat sebelum Fase 6.3).
- `updated_by_device`: diisi setiap UPDATE (perangkat yang terakhir mengedit).

**Keputusan "baris yang sama vs tabrakan" di langkah 1 sync (`_decide_identity`):**
- Cloud `created_by_device == device_id lokal` → **identity** (baris buatan perangkat ini).
- Cloud milik perangkat LAIN → **tabrakan** (baris diberi id cloud baru) — menggantikan heuristik konten-identik yang dulu bisa **menggabungkan dua baris berbeda** dari dua perangkat.
- Cloud masih NULL (baris lama) → heuristik lama tetap dipakai (konten sama / hanya `updated_at` yang beda → identity).
- Kasus aman khusus: baris LOKAL masih NULL (mis. salinan DB lama) + isi identik dengan baris cloud milik perangkat lain → identity (digabung, bukan diduplikasi).

**Perlindungan kepemilikan:**
- `created_by_device` TIDAK PERNAH diubah lewat UPDATE — sync membuang kolom ini saat update cloud (`_without_owner`).
- Kolom kepemilikan dikecualikan dari perbandingan konten (`_same_content` / `_row_comp`) agar baris yang hanya beda meta tidak memicu re-sync.

> ⚠️ **Caveat alur copy DB (INSTALL_GUIDE 3.5-B):** `essa.db` menyimpan `device_id` perangkat
> asal, jadi salinan DB di perangkat kedua akan **mengaku sebagai perangkat yang sama**
> (baris baru tercatat `created_by_device = id` perangkat asal). Bila dua perangkat aktif
> memakai salinan yang sama, rotasi `device_id` di perangkat kedua (hapus baris
> `app_settings.device_id` → aplikasi membuat id baru saat start). `sync_id_map` tidak
> terpengaruh; alur cloud (3.5-A) selalu mendapat id baru dari DB kosong.

**Hasil uji (E2E 2 perangkat `scripts/_test_twoway.py` + regresi `essa.db` asli):**
- [x] Dua perangkat membuat baris KONTEN IDENTIK di id sama → tetap 2 baris (tabrakan), tidak digabung.
- [x] Salinan DB lama (owner NULL) konten identik → identity (tidak diduplikasi).
- [x] `created_by_device` terisi otomatis saat insert via ORM; `updated_by_device` mencatat editor terakhir (LWW).
- [x] Regresi `essa.db` asli + Neon: migration cloud & lokal OK; sync konvergen (0 perubahan); count 26 tabel lokal = cloud (**ALL MATCH**).

---

### FASE 7 — Tombol Sync Manual + Indikator Status Cloud ✅ SELESAI (7 Agu 2026)

Tujuan: memberi kendali manual & visibilitas status cloud langsung dari aplikasi.

**Implementasi (`main.py`):**
- **Indikator status** di footer sidebar (label kecil):
  - `☁ CLOUD NONAKTIF` (abu-abu) — `CLOUD_DATABASE_URL` belum diisi.
  - `☁ CLOUD SIAP · BELUM SYNC` (kuning) — cloud aktif, belum pernah sync.
  - `☁ TERSINKRON · <waktu>` (cyan) — waktu `cloud_last_sync` terakhir.
  - `☁ MENYINKRONKAN...` (kuning) — sedang berjalan.
  - `☁ SYNC OK` / `☁ GAGAL · CEK INTERNET` (cyan/pink) — hasil sync manual.
  - `☁ OFFLINE · SYNC GAGAL` (kuning) — sync terakhir GAGAL (mis. jaringan/DNS);
    tetap tampil sampai sync berikutnya sukses (tombol SYNC NOW tetap aktif).
- **Tombol `⟳ SYNC NOW`** — menjalankan sinkronisasi DUA ARAH di **thread latar**
  (UI tidak membeku), lalu memicu refresh dashboard (`database_changed`).
  Dinonaktifkan saat cloud nonaktif atau saat sync sedang berjalan.
- **Anti double-sync**: flag `_syncing` bersama dipakai tombol manual, auto-pull
  startup, dan `closeEvent` — tidak ada dua transaksi sync yang berjalan
  bersamaan (menutup race di review).

**FASE 7 update (7 Agu 2026) — Resiliensi jaringan/DNS (`utils/cloud_sync.py` + `main.py`):**
- **Retry otomatis**: error jaringan/DNS sementara (mis. Wi-Fi belum siap tepat
  setelah PC dinyalakan → `could not translate host name ... Name or service not known`)
  dicoba ulang sampai **3×** dengan jeda 2,5 detik sebelum dilaporkan. Error
  non-jaringan (kredensial salah, database hilang) langsung dilaporkan tanpa retry.
- **Pesan ramah (Indonesia)**: console tidak lagi menampilkan traceback SQLAlchemy
  mentah — kegagalan DNS/jaringan/autentikasi diklasifikasikan menjadi kalimat
  jelas + konfirmasi **data lokal AMAN**.
- **Status jujur**: hasil kegagalan disimpan di `app_settings` (key `cloud_last_error`,
  otomatis dikosongkan saat sync berikutnya sukses). Label sidebar menampilkan
  `☁ OFFLINE · SYNC GAGAL` (kuning) sampai sync sukses — tidak lagi menampilkan
  `TERSINKRON` yang menyesatkan. Tombol SYNC NOW tetap aktif agar bisa dicoba ulang.
- **closeEvent tanpa retry** (`sync_local_to_cloud(retries=0)`): saat menutup aplikasi,
  kegagalan jaringan tidak menunda keluar aplikasi — sync dicoba lagi otomatis di
  pembukaan berikutnya.

**Verifikasi:**
- [x] Smoke test offscreen: label status benar, tombol aktif/nonaktif sesuai konfigurasi, guard anti-double-sync bekerja.
- [x] Uji retry: error DNS sementara → dicoba ulang lalu sukses; error kredensial → dilaporkan langsung (tanpa retry).
- [x] Regresi: sync nyata ke Neon OK & `cloud_last_error` kosong; status `☁ OFFLINE · SYNC GAGAL` muncul saat error tersimpan & tombol tetap aktif.

---

### FASE 7-B — (Opsional) Dashboard Cloud Read-Only

- Buka data cloud via UI Neon / query langsung untuk laporan ringkas (total omzet, stok, piutang) tanpa membuka aplikasi.
- Tidak menambah beban ke aplikasi lokal.

---

## 6. Inventaris Kolom `updated_at` (untuk Fase 5 & 6)

Kolom ini adalah dasar deteksi perubahan di sinkronisasi. **Status (6 Agu 2026): SEMUA 26 tabel kini punya `updated_at`** — 5 tabel sudah sejak awal (`sku_master`, `persons`, `clients`, `bon_balances`, `app_settings`), dan 21 tabel lain ditambahkan oleh migration `a1b2c3d4e5f6` (di cloud **dan** di `essa.db` lokal).

Kolom dibuat **nullable** (baris lama tetap NULL sampai diubah) dan **diisi otomatis oleh aplikasi** pada setiap insert/update via ORM (`default` + `onupdate=datetime.now`):

| Kelompok | Tabel |
|---|---|
| Sudah punya sejak awal | `sku_master`, `persons`, `clients`, `bon_balances`, `app_settings` |
| Ditambahkan migration `a1b2c3d4e5f6` | `garapan_rates`, `tarif_master`, `master_tarif_penjahit`, `hasil_cutting`, `distribusi_cutting`, `modal_operasional`, `pengeluaran_offline`, `debt_entries`, `debt_payments`, `bon_movements`, `salary_runs`, `salary_line_items`, `pengsup_reconciliation`, `attendance_records`, `invoices`, `invoice_lines`, `client_receivables`, `client_receivable_payments`, `stock_movements`, `profit_history`, `audit_log` |

> Catatan: baris lama yang belum pernah diubah setelah migrasi tetap bernilai `updated_at = NULL`
> (sama di lokal & cloud → tidak memicu sync). Begitu baris diubah aplikasi, nilainya terisi
> dan ikut tersinkron. **Sejak Fase 6.2 kolom ini dipakai untuk resolusi konflik
> *last-write-wins*** pada sinkronisasi dua arah (NULL dianggap paling lama).

> **Fase 6.3:** SEMUA 26 tabel kini juga punya `created_by_device` + `updated_by_device`
> (migration `f6e5d4c3b2a1`, nullable) — **kepemilikan baris antar perangkat**. Diisi otomatis
> oleh aplikasi (event ORM di `data/models/base.py`); dipakai sync untuk memutuskan identity vs
> tabrakan secara PASTI (menggantikan heuristik backfill untuk perangkat standalone). Detail: bagian Fase 6.3.

---

## 7. Keamanan

1. **`CLOUD_DATABASE_URL` hanya di `.env`** — jangan pernah di-hardcode atau di-commit.
2. `.gitignore` harus memuat `.env` (verifikasi file ini).
3. Selalu `sslmode=require` pada koneksi cloud.
4. Di Neon: buat **role khusus** `yazmina_app` dengan password kuat; jangan pakai role owner untuk aplikasi (prinsip least-privilege).
5. Rotasi password bila terjadi kebocoran. Neon punya fitur reset password + revoke.
6. Data sensitif keuangan tersimpan sebagai teks biasa (seperti sekarang) — sinkronisasi cloud membawa data yang sama; pastikan hanya orang terpercaya yang punya akses project Neon.

---

## 8. Rollback & Recovery

| Skenario | Prosedur |
|---|---|
| Aplikasi error setelah Fase 1 | Hapus/kosongkan `.env` → aplikasi otomatis kembali ke SQLite lokal (zero risk). |
| Migration cloud gagal | `alembic downgrade` di URL cloud; atau drop project Neon & buat ulang (free tier, tidak ada data penting sebelum Fase 4). |
| Data lokal rusak | Restore dari `backups/essa_backup_*.db` (engine lama tetap jalan) atau dari cloud via `scripts/restore_from_cloud.py`. |
| Sync konflik tidak diinginkan | Nonaktifkan `DATABASE_URL` sementara → semua perangkat kembali mode lokal murni. |
| Ingin mulai ulang dari awal | Drop semua tabel cloud, jalankan ulang Fase 3–4. |

**Aturan emas:** aplikasi lokal **tidak pernah** bergantung pada ketersediaan cloud. Matikan internet → aplikasi harus tetap 100% berfungsi.

---

## 9. Checklist Uji Coba (per fase)

- [ ] **F0** URL cloud bisa dikoneksi dari laptop.
- [ ] **F1** Aplikasi jalan normal tanpa `.env` (mode SQLite).
- [ ] **F1** `engine.url` benar saat `.env` diisi.
- [ ] **F2** `alembic upgrade head` sukses penuh di Postgres kosong.
- [ ] **F3** 26 tabel + `alembic_version` terakhir ada di cloud.
- [ ] **F4** Jumlah baris per tabel identik lokal vs cloud.
- [ ] **F4** Relasi teruji: 1 invoice + lines terbaca utuh di cloud.
- [ ] **F5** Edit data → tutup app → baris ter-update di cloud.
- [ ] **F5** Soft-delete → `is_deleted=1` ter-sync (bukan terhapus fisik).
- [ ] **F6** Perangkat B menarik data A; perubahan B terlihat di A (uji 2 komputer).
- [ ] **R1** Internet dimatikan → semua menu aplikasi tetap berfungsi penuh.
- [ ] **R2** `DATABASE_URL` dikosongkan → aplikasi kembali normal tanpa error.

---

## 10. Daftar File yang Akan Diubah / Ditambah (Tentatif)

| File | Perubahan |
|---|---|
| `data/database.py` | Refactor: env URL + guard PRAGMA + `pool_pre_ping` |
| `data/migrations/versions/d8e3f4a5b6c7_*.py` | Perbaikan `last_insert_rowid()` & `datetime('now')` |
| `data/migrations/versions/xxxx_add_updated_at_all.py` | **Baru** — kolom `updated_at` utk 21 tabel |
| `utils/cloud_sync.py` | **Baru** — engine sinkronisasi (Fase 5) |
| `utils/backup_engine.py` | Perluas: backup lokal tetap + trigger sync cloud |
| `main.py` | Panggil sync di `closeEvent` (setelah backup lokal) |
| `scripts/create_cloud_schema.py` | **Baru** — buat skema cloud dari model (Fase 3) |
| `scripts/seed_cloud.py` | **Baru** — one-time initial seed (Fase 4) |
| `scripts/restore_from_cloud.py` | **Baru** — recovery (Fase 8) |
| `.env` | **Baru** — menyimpan `CLOUD_DATABASE_URL` (dijaga via `.gitignore`) |
| `.gitignore` | Pastikan memuat `.env` |
| `requirements.txt` | + `psycopg2-binary`, `python-dotenv` |
| `ui/components/buttons.py` / sidebar | Tombol "Sync ke Cloud" + indikator status (opsional) |

---

## 11. Log Keputusan

| Tanggal | Keputusan | Alasan |
|---|---|---|
| 05-08-2026 | Arsitektur hybrid (SQLite lokal + cloud) | Aplikasi wajib offline; cloud = backup + sync |
| 05-08-2026 | Cloud DB = **Neon** | Postgres murni, free tier cukup, koneksi langsung, kompatibel SQLAlchemy/Alembic |
| 05-08-2026 | Firebase ditolak | NoSQL tidak cocok dgn 26 tabel relasional → butuh tulis ulang aplikasi |
| 05-08-2026 | Urutan implementasi: F0→F6 bertahap | Menekan risiko; setiap fase memberi nilai nyata lebih dulu (backup dulu, baru multi-device) |
| 05-08-2026 | Rebranding aplikasi: ESSA STORE → **Yazmina Hijab** (semua teks tampilan, PDF, README) | Sesuai permintaan; nama file DB `essa.db` sementara dipertahankan karena sedang dipakai aplikasi (rename opsional saat app ditutup) |
| 05-08-2026 | **Fase 3–4 dieksekusi**: skema cloud dibuat dari model (`create_all` + `alembic stamp head` = e4fc4d7866da); seed 3.840 baris (26 tabel) dengan ID dipertahankan | Semua count lokal = cloud (ALL MATCH); FK `0`/dangling → NULL; kolom generated `nama_uppercase` diisi otomatis Postgres |
| 05-08-2026 | **Fase 5 dieksekusi**: `utils/cloud_sync.py` (diff-sync satu arah) terpasang di `closeEvent` `main.py`; sync manual via `python -m utils.cloud_sync` | Terverifikasi konvergen. Perbaikan selama uji: (1) normalisasi string datetime SQLite; (2) kolom cloud `salary_line_items.qty` → DOUBLE PRECISION (data lokal berisi pecahan); heartbeat `cloud_last_sync` di `app_settings` |
| 06-08-2026 | **Fase 5.5 dieksekusi**: pull dua arah aman (`pull_from_cloud` mode setup/merge), auto-pull perangkat baru di `main.py`, `device_id` per perangkat, pengaman DELETE push untuk multi-perangkat | Aturan konflik: **perangkat yang sedang dipakai menang** — pull tidak pernah menghapus data lokal; pengaman mencegah perangkat DB lama menghapus data cloud perangkat lain |
| 06-08-2026 | **Fondasi Fase 6**: migration `a1b2c3d4e5f6` (kolom `updated_at` 21 tabel) diterapkan ke cloud | Kolom siap; pengisian otomatis oleh app + penerapan ke lokal dijadwalkan di Fase 6 |
| 06-08-2026 | **Fase 6 bagian 1 (jalur tulis) dieksekusi**: ke-21 model diberi kolom `updated_at` (nullable, default + onupdate) → semua tulis ORM mengisinya; migration `a1b2c3d4e5f6` diterapkan ke `essa.db` lokal | Terverifikasi: 19 asersi jalur tulis PASS, push konvergen (hanya heartbeat), pull setup 3.867 baris OK dengan kolom baru |
| 06-08-2026 | **Fase 6.2 (ID mapping + LWW + delete dua arah) dieksekusi**: `sync_id_map` lokal (id lokal→id cloud + tombstone + last_seen), alokasi id cloud baru saat tabrakan, terjemahan FK, *last-write-wins* via `updated_at`, delete berbasis pemetaan, resiliensi konflik index unik (savepoint + peringatan); auto-sync dua arah saat app dibuka & ditutup | Uji E2E 2 perangkat lulus (tabrakan id, FK, LWW, delete, konvergen); regresi `essa.db` asli 0 perubahan, count lokal=cloud (ALL MATCH). Perbaikan saat uji: (1) self-FK `0`→NULL saat perbandingan agar baris sama tidak dianggap tabrakan; (2) perbandingan tanpa kolom pk (baris remap); (3) pemetaan baris yang ditarik ikut masuk peta terjemahan FK |
| 07-08-2026 | **Fase 6.3 (kepemilikan perangkat) dieksekusi**: kolom `created_by_device`/`updated_by_device` (nullable) di 26 tabel — migration `f6e5d4c3b2a1` diterapkan ke cloud (Neon) & `essa.db` lokal; event ORM `before_insert`/`before_update` di `data/models/base.py` mengisinya otomatis (`CURRENT_DEVICE_ID` di-set `main.py` & sync); `_decide_identity` memakai kepemilikan (milik kita → identity, milik perangkat lain → tabrakan, NULL → heuristik lama); kepemilikan tidak pernah berubah via update; `main.py` memanggil `ensure_device_id()` saat start | Uji E2E 2 perangkat lulus (konten identik dari 2 perangkat → tetap 2 baris; salinan DB lama → identity tanpa duplikat; owner terisi via ORM; updated_by_device = editor terakhir); regresi `essa.db` asli + Neon: sync konvergen 0 perubahan, count 26 tabel lokal = cloud (ALL MATCH) |

---

*Dokumen ini adalah pedoman hidup — perbarui `## 11. Log Keputusan` setiap kali ada keputusan arsitektur baru selama implementasi.*
