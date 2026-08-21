# ☁️ Sistem Database Cloud — Yazmina Hijab (Penjelasan Teknis Lengkap)

> Dokumen ini menjelaskan **bagaimana sistem database cloud yang dibangun pada aplikasi Yazmina Hijab bekerja secara teknis** — arsitektur, teknologi yang digunakan, mekanisme sinkronisasi dua arah, resolusi konflik, hingga batasannya. Ini adalah penjelasan "cara kerja mesin", sedangkan panduan langkah demi langkah migrasi ada di [`CLOUD_DATABASE_GUIDE.md`](CLOUD_DATABASE_GUIDE.md) dan panduan instalasi perangkat baru di [`INSTALL_GUIDE.md`](INSTALL_GUIDE.md).

---

## Daftar Isi

1. [Gambaran Besar: Arsitektur Hybrid](#1-gambaran-besar-arsitektur-hybrid)
2. [Teknologi yang Digunakan](#2-teknologi-yang-digunakan)
3. [Dua Mesin Database (`data/database.py`)](#3-dua-mesin-database-datadatabasepy)
4. [Kapan Sinkronisasi Terjadi?](#4-kapan-sinkronisasi-terjadi)
5. [Mekanisme Inti: Sinkronisasi Dua Arah per Tabel](#5-mekanisme-inti-sinkronisasi-dua-arah-per-tabel)
6. [Lapisan ID Mapping — Masalah Terbesar Multi-Perangkat](#6-lapisan-id-mapping--masalah-terbesar-multi-perangkat)
7. [Kepemilikan Baris (`created_by_device` / `updated_by_device`)](#7-kepemilikan-baris-created_by_device--updated_by_device)
8. [Resolusi Konflik: Last-Write-Wins (LWW)](#8-resolusi-konflik-last-write-wins-lww)
9. [Delete Dua Arah (Tombstone)](#9-delete-dua-arah-tombstone)
10. [Resiliensi & Pengaman](#10-resiliensi--pengaman)
11. [Metadata yang Ikut Tersinkron](#11-metadata-yang-ikut-tersinkron)
12. [Alur Perangkat Baru (Setup)](#12-alur-perangkat-baru-setup)
13. [Peta File Penting](#13-peta-file-penting)
14. [Batasan yang Perlu Diketahui](#14-batasan-yang-perlu-diketahui)

---

## 1. Gambaran Besar: Arsitektur Hybrid

Sistem ini **bukan** "pindah database ke cloud", melainkan **dua database yang hidup berdampingan dan saling sinkron**:

```
┌─────────────────────── LOKAL (PC) ─────────────────────────────┐
│  essa.db  (SQLite)                    ← DATABASE KERJA          │
│  • Aplikasi baca/tulis di sini setiap hari                      │
│  • Offline-first: 100% berfungsi tanpa internet                 │
└──────────────┬──────────────────────────────────────────────────┘
               │  sinkronisasi DUA ARAH (utils/cloud_sync.py)
               ▼
┌─────────────────────── CLOUD (Neon) ────────────────────────────┐
│  PostgreSQL serverless (yazmina_hijab)   ← BACKUP + PUSAT DATA  │
│  • Salinan semua data (26 tabel)                                │
│  • Perangkat lain menarik/mengirim data lewat sini              │
└──────────────────────────────────────────────────────────────────┘
```

**Prinsip emas yang tidak pernah dilanggar:** aplikasi **tidak pernah bergantung pada ketersediaan cloud**. Matikan internet → aplikasi tetap berfungsi penuh. Cloud hanyalah "cermin" yang disinkronkan secara berkala.

| Karakteristik | Nilai |
|---|---|
| Database kerja | `essa.db` (SQLite) — selalu lokal, offline-first |
| Database cloud | Neon PostgreSQL serverless (free tier) |
| Arah sinkronisasi | **Dua arah** (lokal ⇄ cloud) |
| Pemicu | Otomatis saat aplikasi dibuka & ditutup; tombol **SYNC NOW** di sidebar; manual via CLI |
| Garansi | Tidak pernah menggagalkan/memblokir aplikasi |

---

## 2. Teknologi yang Digunakan

| Teknologi | Peran | Keterangan |
|---|---|---|
| **SQLite** | Database kerja lokal | Satu file `essa.db`; tanpa server, tanpa instalasi, portabel |
| **PostgreSQL (Neon)** | Database cloud | Serverless — "tidur" saat idle ±5 menit, bangun otomatis saat dipanggil. Free tier: 0.5 GB storage + 100 jam/bulan |
| **SQLAlchemy 2.0 ORM** | Jembatan Python ⇄ database | Gaya modern `Mapped` / `mapped_column`. Satu kode berbicara ke dua dialek (SQLite & Postgres) |
| **Alembic** | Migrasi skema | Mengubah struktur tabel bertahap (menambah kolom), bisa di-rollback |
| **psycopg2** | Driver Postgres untuk Python | Hanya dipakai skrip sinkronisasi/migrasi |
| **python-dotenv** | Pembaca `.env` | Menyimpan `CLOUD_DATABASE_URL` (rahasia, tidak di-commit) |
| **PySide6 (Qt 6)** | Aplikasi desktop | UI + thread latar untuk sinkronisasi non-blocking |

**Kenapa Postgres/Neon, bukan Firebase?** Karena aplikasi ini punya **26 tabel relasional dengan foreign key**. Firebase (NoSQL) tidak mendukung relasi itu tanpa menulis ulang seluruh aplikasi. Postgres = SQL murni → migration, ORM, dan relasi berjalan hampir tanpa perubahan kode.

---

## 3. Dua Mesin Database (`data/database.py`)

```python
DATABASE_URL        → SQLite  (essa.db)    → engine            → dipakai APLIKASI
CLOUD_DATABASE_URL  → Neon (Postgres)      → get_cloud_engine() → dipakai SKRIP SYNC
```

- **`engine`** = koneksi aplikasi, selalu SQLite. Di-set dengan:
  - `PRAGMA journal_mode=WAL` — mode journal agar baca/tulis cepat & aman.
  - `PRAGMA busy_timeout=5000` — tunggu maksimal 5 detik bila DB sedang dikunci proses lain (mis. auto-sync di thread latar).
- **`get_cloud_engine()`** = koneksi cloud, dibuat *lazy* (hanya saat dibutuhkan). Bila `CLOUD_DATABASE_URL` tidak diisi di `.env` → mengembalikan `None` → semua fungsi sync otomatis dilewati dengan aman.
- URL cloud dibaca dari `.env`, bukan di-hardcode → rahasia tidak pernah masuk kode/git.

---

## 4. Kapan Sinkronisasi Terjadi?

| Momen | Dipanggil | Arah |
|---|---|---|
| **Aplikasi dibuka** | `maybe_auto_pull()` di **thread latar** (window tetap tampil, tidak membeku saat Neon cold-start) | Dua arah |
| **Aplikasi ditutup** | `sync_local_to_cloud()` di `closeEvent` (setelah backup lokal) | Dua arah |
| **Tombol SYNC NOW (Fase 7)** | `_CloudSyncWorker` (QThread) di **thread latar** — UI tidak membeku; hasilnya memicu refresh dashboard | Dua arah |
| **Manual (CLI)** | `python -m utils.cloud_sync` (dua arah) · `--pull setup` (perangkat baru) · `--pull merge` (gabung) | Dua arah |

Semua panggilan dibungkus `try/except` — **tidak pernah memperlambat atau menggagalkan penutupan aplikasi** walau internet mati.

**Fase 7 — kontrol manual & visibilitas status (7 Agu 2026):** sidebar menampilkan indikator status cloud
(`☁ CLOUD NONAKTIF` / `☁ SIAP · BELUM SYNC` / `☁ TERSINKRON · <waktu>` / `☁ MENYINKRONKAN...`) dan tombol
**⟳ SYNC NOW** yang menjalankan sinkronisasi dua arah di thread latar lalu me-refresh dashboard.
Flag `_syncing` **dipakai bersama** tombol manual, auto-pull startup, dan `closeEvent` — menjamin tidak ada
dua transaksi sync yang berjalan bersamaan.

**Resiliensi jaringan (7 Agu 2026):** bila sync gagal karena **DNS/jaringan sementara** (mis. Wi-Fi belum siap
saat PC baru dinyalakan — `could not translate host name ... Name or service not known`), sync **dicoba ulang
otomatis hingga 3×** (jeda 2,5 detik); error non-jaringan (kredensial/database) langsung dilaporkan tanpa retry.
Kegagalan dicatat di `app_settings.cloud_last_error` dan label sidebar menampilkan **`☁ OFFLINE · SYNC GAGAL`**
(kuning) sampai sync berikutnya sukses — tidak menampilkan `TERSINKRON` yang menyesatkan. Tombol SYNC NOW
tetap aktif agar bisa dicoba ulang. Pesan error di console diklasifikasikan menjadi kalimat ramah berbahasa
Indonesia (bukan traceback mentah). Jalur penutupan aplikasi memakai `retries=0` agar keluar tidak tertunda.

Selain cloud, setiap penutupan aplikasi menjalankan **backup lokal** (`utils/backup_engine.py`): `essa.db` disalin dengan API backup bawaan SQLite (aman dari korupsi) ke folder `backups/`, menyimpan 30 backup terakhir. Jadi ada **tiga lapis pengaman**: backup lokal, cloud Neon, dan file `essa.db` itu sendiri.

---

## 5. Mekanisme Inti: Sinkronisasi Dua Arah per Tabel

### 5.1 Alur umum (`_run_sync`)

```
1. Cek koneksi cloud → tidak ada? selesai (status "skipped").
2. Pastikan skema lokal ada (create_all — aman, tidak mengubah tabel lama).
3. Refleksikan skema cloud & lokal → hitung kolom yang sama ("sync columns").
4. Mode "auto": lokal kosong → setup (unduh penuh); ada data → sync dua arah.
5. Buka SATU transaksi besar (all-or-nothing):
   a. Baca device_id perangkat ini (app_settings).
   b. Untuk tiap tabel (urutan INDUK → ANAK): hitung rencana (plan).
   c. Eksekusi INSERT/UPDATE (induk dulu).
   d. Eksekusi DELETE (anak dulu — kebalikan urutan).
   e. Catat metadata: device_id, cloud_last_sync, cloud_last_pull.
6. Sukses → selaraskan sequence Postgres (agar id otomatis tidak bentrok).
```

**Kenapa urutan induk→anak?** Karena foreign key. Anak (mis. `invoice_lines`) menunjuk induk (`invoices`). Induk harus ada dulu di sisi tujuan sebelum anak di-insert, agar FK tidak melanggar. Urutan lengkap ada di `utils/sync_tables.py` (`TABLE_ORDER`).

### 5.2 Perencanaan per tabel — 5 langkah

Untuk tiap tabel, sistem membaca seluruh baris lokal & cloud lalu membandingkan **per primary key**:

| Langkah | Keputusan |
|---|---|
| **1. Baris lokal baru (belum punya pemetaan)** | Apakah baris yang sama dengan baris cloud di id yang sama, atau baris berbeda? → lihat bagian [6](#6-lapisan-id-mapping--masalah-terbesar-multi-perangkat) |
| **2. Baris lokal baru** | **INSERT ke cloud** (pakai id sama / id cloud baru), catat pemetaan |
| **3. Baris terpetakan, lokal masih ada** | Bandingkan isi: sama → diam; beda → **last-write-wins** (yang `updated_at`-nya lebih baru menang); seri → perangkat yang dipakai menang |
| **4. Baris terpetakan, lokal sudah dihapus** | **Tombstone**: hapus di cloud (kecuali cloud diedit perangkat lain setelahnya) |
| **5. Baris cloud baru (belum dikenal lokal)** | **INSERT ke lokal** (tarik), catat pemetaan |

### 5.3 Normalisasi nilai (agar perbandingan adil)

SQLite dan Postgres menyimpan data sedikit berbeda, jadi sebelum dibandingkan semua nilai "dibakukan" (`_norm`):

- **Datetime** → string kanonik `YYYY-MM-DD HH:MM:SS.ffffff` (mis. `2026-08-01 09:00:00.000000` dianggap sama dengan `2026-08-01 09:00:00`).
- **Kolom computed** (mis. `persons.nama_uppercase` yang diisi otomatis server) → **tidak pernah** ikut disinkronkan/dibandingkan.
- **FK menunjuk id tak dikenal** (mis. `parent_sku_id = 0` pada data lama) → dinormalisasi ke `NULL`, baik saat perbandingan maupun penulisan, agar tidak dianggap beda dan tidak melanggar constraint Postgres.

Tanpa normalisasi ini, setiap sync akan melihat "beda" terus → re-sync tanpa henti (tidak konvergen).

---

## 6. Lapisan ID Mapping — Masalah Terbesar Multi-Perangkat

### 6.1 Masalahnya

Dua perangkat masing-masing punya id autoincrement mulai dari **1**. Jadi `persons id=1` di PC A bisa berarti *"Andi"*, sedangkan di PC B bisa berarti *"Orang B"* — **id yang sama menunjuk baris yang berbeda**.

### 6.2 Solusinya: tabel `sync_id_map` (khusus lokal, TIDAK pernah disinkronkan)

```
sync_id_map (
  table_name TEXT,   -- nama tabel
  local_id   INT,    -- id di perangkat ini
  cloud_id   INT,    -- id yang sebenarnya di cloud
  deleted_at TEXT,   -- tombstone (waktu baris ini dihapus lokal)
  last_seen  TEXT,   -- terakhir kali baris ini sinkron
)
```

### 6.3 Dua kemungkinan saat baris lokal bertemu cloud di id yang sama

- **Identity mapping (baris yang sama)** → id dipakai apa adanya; pemetaan `local_id = cloud_id`.
- **Collision / remap (baris berbeda)** → baris lokal diberi **id cloud BARU** (`MAX(id)+1` yang dijamin unik per-run), pemetaan `local_id → cloud_id_baru` dicatat. **Tidak ada data yang hilang** — kedua baris tetap hidup, hanya id cloud-nya berbeda.

### 6.4 Terjemahan Foreign Key

Saat baris anak disinkronkan, FK-nya **diterjemahkan lewat pemetaan**. Contoh: `invoice_lines.invoice_id=1` lokal → di cloud menjadi id invoice yang benar (misal 4). Ini dilakukan lewat peta dua arah `l2c` (lokal→cloud) dan `c2l` (cloud→lokal) yang diisi bertahap mengikuti urutan induk→anak.

---

## 7. Kepemilikan Baris (`created_by_device` / `updated_by_device`)

Ini adalah "tanda tangan" perangkat pada setiap baris:

| Kolom | Diisi saat | Arti |
|---|---|---|
| `created_by_device` | INSERT (event ORM di `data/models/base.py`) | ID perangkat pembuat baris |
| `updated_by_device` | UPDATE | ID perangkat yang terakhir mengedit |

**Bagaimana diisi otomatis tanpa menyentuh tampilan?** Di `data/models/base.py` ada **event ORM** (`before_insert` / `before_update` dengan `propagate=True`) yang berjalan setiap kali baris disimpan lewat ORM. Nilai `CURRENT_DEVICE_ID` di-set saat aplikasi start (`ensure_device_id()` di `main.py`) dan saat sync — diambil dari `app_settings.device_id` (UUID 8 karakter, unik per perangkat, dibuat sekali).

**Kegunaannya** — menggantikan "tebak-tebakan" saat perangkat standalone bergabung:

- Baris cloud bertanda `device_id` kita → pasti baris kita (**identity**).
- Baris cloud bertanda perangkat **lain** → baris berbeda → **tabrakan** (diberi id cloud baru), meskipun isinya identik.
- Baris lama tanpa tanda (NULL) → tetap memakai heuristik isi (kompatibilitas mundur).
- `created_by_device` **tidak pernah berubah lewat update** — kepemilikan permanen.

---

## 8. Resolusi Konflik: Last-Write-Wins (LWW)

Bila dua perangkat mengedit baris yang sama:

```
updated_at lokal  >  updated_at cloud  →  PUSH lokal ke cloud
updated_at cloud  >  updated_at lokal  →  PULL cloud ke lokal
sama (seri)                            →  perangkat yang sedang dipakai menang
```

- `updated_at = NULL` dianggap **paling lama** (baris yang belum pernah diubah).
- Timestamp dibandingkan sebagai string kanonik → konsisten lintas SQLite/Postgres.
- `updated_at` diisi otomatis oleh aplikasi (`default` + `onupdate=datetime.now` di model); migration `a1b2c3d4e5f6` menambahkan kolom ini ke 21 tabel yang belum punya (diterapkan di cloud & `essa.db` lokal).

> ⚠️ **Catatan:** saat ini memakai waktu lokal perangkat. Untuk toko satu zona waktu tidak masalah; bila perangkat tersebar lintas zona waktu, sebaiknya diganti ke UTC (sudah tercatat di panduan).

---

## 9. Delete Dua Arah (Tombstone)

| Skenario | Perilaku |
|---|---|
| Baris **dihapus lokal** | Pemetaan diberi tombstone `deleted_at`; baris cloud ikut dihapus — **kecuali** cloud sudah diubah perangkat lain setelah sync terakhir (edit itu menang, tombstone ditunda) |
| Baris **dihapus di cloud** (perangkat lain) | Baris lokal ikut dihapus — **kecuali** perangkat ini mengeditnya setelah sync terakhir (edit lokal menang → baris "dihidupkan kembali" di id yang sama) |
| Baris perangkat lain yang **belum pernah ditarik** | Tidak ikut terhapus (tidak ada pemetaan → aman) |
| Total baris lokal = 0 (lokasi DB salah) | Penghapusan cloud **dibatalkan** — backup tidak ikut terhapus |

---

## 10. Resiliensi & Pengaman

1. **Konflik index unik** (mis. dua perangkat membuat `kode_sku` sama): baris bermasalah **dilewati per-baris** (savepoint + peringatan di console) — tidak menggagalkan seluruh sync. Baris tetap ada di sisinya dan dicoba lagi di sync berikutnya.
2. **All-or-nothing**: semua operasi cloud & lokal dalam satu transaksi — gagal di tengah tidak menyisakan separuh-selesai.
3. **Tidak pernah melempar exception** ke aplikasi (dibungkus `try/except`).
4. **Sequence Postgres diselaraskan** setelah sync sukses, agar insert id eksplisit tidak membuat auto-id bentrok di masa depan.
5. **`connect_timeout=5s`** pada engine cloud agar penutupan aplikasi tidak menggantung saat Neon dingin (auto-suspend).
6. **Retry otomatis** untuk kegagalan DNS/jaringan sementara (hingga 3×, jeda 2,5 detik) — pemulihan sendiri saat jaringan kembali normal; jalur penutupan aplikasi menonaktifkan retry (`retries=0`) agar tidak menunda keluar.
7. **Pesan error ramah**: kegagalan DNS/jaringan/autentikasi diklasifikasikan (`_friendly_error`) menjadi kalimat jelas + konfirmasi data lokal aman; status UI jujur (`☁ OFFLINE · SYNC GAGAL`) hingga sync sukses.

---

## 11. Metadata yang Ikut Tersinkron

| Key `app_settings` | Isi |
|---|---|
| `device_id` | UUID 8 karakter identitas perangkat (tidak tertimpa perangkat lain) |
| `cloud_last_sync` | Waktu sync terakhir (heartbeat) |
| `cloud_last_pull` | Waktu pull terakhir |
| `cloud_last_error` | Pesan kegagalan sync terakhir (kosong = semua baik) — dipakai status UI |

Metadata ini di-push satu arah (lokal→cloud) dan menjadi penanda "sistem ini aktif".

---

## 12. Alur Perangkat Baru (Setup)

1. Salin folder proyek + `.env` (tanpa `essa.db`).
2. Jalankan aplikasi saat internet tersedia → `maybe_auto_pull()` mendeteksi **DB lokal kosong** → mode **setup**: seluruh data cloud diunduh (26 tabel, ±3.800 baris); id cloud dipakai apa adanya bila bebas, atau diberi id lokal baru bila bertabrakan (pemetaan dicatat).
3. Setelah itu aplikasi berjalan offline normal; sync dua arah aktif untuk seterusnya.
4. Bila otomatis gagal (internet mati saat pertama dibuka): `python -m utils.cloud_sync --pull setup`.

---

## 13. Peta File Penting

| File | Isi |
|---|---|
| `data/database.py` | Engine SQLite + engine cloud (lazy) |
| `data/models/*.py` | 26 model ORM + kolom `updated_at`, `created_by_device`, `updated_by_device` |
| `data/models/base.py` | `Base` + event pengisi kepemilikan perangkat |
| `utils/cloud_sync.py` | **Jantung sinkronisasi**: perencanaan, ID mapping, LWW, tombstone, kepemilikan |
| `utils/sync_tables.py` | Urutan pemrosesan 26 tabel (induk→anak) |
| `data/migrations/versions/*.py` | 5 migration Alembic (terakhir: `f6e5d4c3b2a1`) |
| `main.py` | Pemicu auto-sync (startup thread + closeEvent), **tombol SYNC NOW + indikator status cloud** di sidebar (Fase 7), `ensure_device_id()` |
| `utils/backup_engine.py` | Backup lokal (30 file terakhir) |
| `scripts/_test_twoway.py` | Uji E2E 2 perangkat (18 langkah) |
| `scripts/_verify_all_counts.py` | Cek kesesuaian jumlah baris lokal vs cloud |

---

## 14. Batasan yang Perlu Diketahui

1. **Konflik bisnis sejati** (duplikat `kode_sku` lintas perangkat) tidak bisa diselesaikan mesin — dilewati dengan peringatan di console sampai dirapikan manual.
2. **Baris lama tanpa pemilik** (sebelum Fase 6.3) masih memakai heuristik konten — hanya jendela transisi; baris baru sudah pasti kepemilikannya.
3. **Menyalin `essa.db`** ke perangkat kedua ikut menyalin `device_id` → perangkat kedua "mengaku" sebagai perangkat pertama. Solusi: rotasi `device_id` sekali saja (hapus baris `app_settings.device_id` → aplikasi membuat id baru saat start). Alur cloud (DB kosong) selalu aman.
4. **Zona waktu**: LWW memakai waktu lokal — aman selama semua perangkat dalam satu zona waktu.
5. **Cloud ≠ pengganti database kerja**: cloud hanya lapisan backup + sinkronisasi; aplikasi wajib tetap berfungsi offline.

---

*Dokumen ini adalah penjelasan teknis — lihat [`CLOUD_DATABASE_GUIDE.md`](CLOUD_DATABASE_GUIDE.md) untuk panduan migrasi bertahap dan [`INSTALL_GUIDE.md`](INSTALL_GUIDE.md) untuk setup perangkat baru.*
