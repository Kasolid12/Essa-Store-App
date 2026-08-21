# 📦 PANDUAN INSTALASI & SETUP PERANGKAT BARU — YAZMINA HIJAB

> Panduan langkah demi langkah untuk memasang aplikasi **Yazmina Hijab (Operations OS)** di komputer baru, memindahkan data, dan memastikan semuanya berjalan.

| | |
|---|---|
| **Aplikasi** | Yazmina Hijab — Operations OS (desktop, PySide6) |
| **Mode utama** | **Offline-first** — aplikasi berjalan penuh tanpa internet |
| **Cloud (opsional)** | Backup/sinkronisasi ke Neon PostgreSQL (lihat `CLOUD_DATABASE_GUIDE.md`) |
| **Terakhir diperbarui** | 7 Agustus 2026 |

---

## 1. Ringkasan

Yang perlu dilakukan untuk memakai aplikasi di perangkat baru:

1. ✅ Menyalin folder proyek (kode aplikasi)
2. ✅ Menginstall Python & dependensi
3. ✅ **Membawa data** — pilih salah satu:
   - **Cara A (cloud aktif, disarankan):** tidak perlu menyalin `essa.db` — data otomatis **diunduh dari cloud** saat aplikasi pertama dibuka (lihat 3.5-A).
   - **Cara B (tanpa cloud):** salin file `essa.db` dari perangkat lama (lihat 3.5-B).
4. ✅ (Opsional) Menyalin `.env` agar koneksi cloud ikut terbawa
5. ✅ Menjalankan aplikasi

> 💡 **Aplikasi tidak butuh internet untuk dipakai.** Koneksi cloud (`CLOUD_DATABASE_URL`) hanya diperlukan untuk skrip backup/sinkronisasi — jika tidak disiapkan, aplikasi tetap berjalan normal secara offline.

---

## 2. Kebutuhan Sistem

| Komponen | Syarat |
|---|---|
| Sistem Operasi | Windows 10/11 (64-bit) — panduan ini; Linux/macOS juga didukung |
| Python | **3.11 atau lebih baru** (diuji pada 3.11.x) |
| Ruang disk | ± 500 MB (aplikasi + data) |
| RAM | 4 GB (cukup) |
| Internet | **Tidak wajib** untuk menjalankan aplikasi |

---

## 3. Cara 1 — Instalasi dari Folder Proyek (disarankan)

### 3.1 Salin folder proyek ke perangkat baru

Salin **seluruh folder proyek** (mis. `Essa-Store-App`) dari perangkat lama ke perangkat baru — bisa lewat flashdisk, Google Drive, atau jaringan. Pastikan folder berisi file berikut:

```
Essa-Store-App/
├── main.py                  ← pintu masuk aplikasi
├── start_app.bat            ← cara TERBAIK membuka aplikasi (double-click)
├── requirements.txt         ← daftar dependensi
├── alembic.ini
├── data/                    ← kode database & model
├── ui/                      ← kode antarmuka
├── utils/                   ← PDF, backup
├── assets/                  ← logo & aset (wajib ada, dipakai PDF invoice)
└── ...
```

### 3.2 Install Python

1. Unduh Python 3.11+ dari **https://www.python.org/downloads/**.
2. Saat instalasi, **centang** opsi **"Add Python to PATH"** (penting!).
3. Verifikasi di terminal/CMD:
   ```bash
   python --version
   ```
   Harus muncul misalnya `Python 3.11.15`.

### 3.3 (Disarankan) Buat virtual environment

Di dalam folder proyek, jalankan:

```bash
python -m venv venv
```

Aktifkan:
- **Command Prompt:** `venv\Scripts\activate`
- **PowerShell:** `venv\Scripts\Activate.ps1`
- **Git Bash / bash:** `source venv/Scripts/activate`

Setelah aktif, prompt terminal diawali `(venv)`.

### 3.4 Install dependensi

```bash
pip install -r requirements.txt
```

Dependensi yang terinstall: PySide6, SQLAlchemy, Alembic, ReportLab, OpenPyXL, Pandas, Loguru, python-dotenv, psycopg2-binary.

### 3.5 ⭐ Bawa data ke perangkat baru

Agar data toko (SKU, hutang, gaji, stok, dll.) ikut terbawa, pilih salah satu cara di bawah.

#### 3.5-A (Disarankan jika cloud aktif) — Unduh otomatis dari cloud

Jika perangkat lama sudah punya koneksi cloud (`CLOUD_DATABASE_URL` di `.env`):

1. Salin folder proyek **tanpa** `essa.db` (atau biarkan aplikasi membuat `essa.db` kosong).
2. Salin file **`.env`** dari perangkat lama (lihat 3.6) — ini kunci agar aplikasi tahu alamat cloud.
3. Jalankan `python main.py` saat **internet tersedia** (cukup pertama kali saja).
4. Aplikasi mendeteksi DB lokal kosong → otomatis **mengunduh seluruh data dari cloud** ke `essa.db`.
   Setelah selesai, data muncul di dashboard dan aplikasi berjalan offline seperti biasa.

> Jika unduhan otomatis tidak terjadi (mis. internet mati saat pertama dibuka), jalankan manual:
> `python -m utils.cloud_sync --pull setup` (dengan `.env` terisi).
>
> 💡 **Sejak Fase 6.2, sinkronisasi DUA ARAH penuh berjalan otomatis**: setiap kali
> aplikasi dibuka dan ditutup, data disinkronkan ke cloud DAN dari cloud (perangkat
> baru/lain). Konflik edit diselesaikan dengan *last-write-wins* (yang lebih baru
> menang). Perangkat baru yang kosong cukup sekali dibuka → seluruh data muncul.

#### 3.5-B (Tanpa cloud) — Salin file `essa.db`

1. **Tutup aplikasi** di perangkat lama terlebih dahulu (agar file database tidak terkunci).
2. Salin file **`essa.db`** dari folder proyek lama ke folder proyek baru (letakkan di root, sejajar dengan `main.py`).
   > Jika di perangkat lama aplikasi masih terbuka saat menyalin, ikutkan juga file `essa.db-wal` dan `essa.db-shm` (bila ada). Cara paling aman: tutup aplikasi, baru salin `essa.db` saja.
3. (Opsional) Jika ingin membawa riwayat backup, salin juga folder **`backups/`**.

> ⚠️ **Tanpa `essa.db` dan tanpa cloud**, aplikasi tetap bisa dibuka, tetapi akan membuat
> **database baru yang kosong** (data tidak otomatis muncul). Jangan panik — database lama
> masih aman di perangkat lama.

> ⚠️ **Khusus Fase 6.3 (kepemilikan perangkat):** `essa.db` menyimpan `device_id` perangkat
> asal. Jika file salinan ini dipakai **bersamaan** dengan perangkat asal (dua komputer
> aktif memakai salinan yang sama), keduanya akan mengaku sebagai perangkat yang sama
> (baris baru tercatat dibuat oleh id yang sama). Agar tiap perangkat punya identitas unik:
> 1. Buka aplikasi perangkat baru **sekali** (biarkan data terunduh/salinan aktif).
> 2. Tutup aplikasi, lalu rotasi identitas perangkat (sekali saja):
>    ```bash
>    python -c "import sqlite3; c=sqlite3.connect('essa.db'); import uuid; c.execute(\"DELETE FROM app_settings WHERE key='device_id'\"); c.commit(); c.close()"
>    ```
> 3. Buka kembali aplikasi → aplikasi membuat `device_id` baru secara otomatis. Pemetaan
>    id (`sync_id_map`) tidak terpengaruh; hanya identitas kepemilikan yang diperbarui.
>    (Alur cloud 3.5-A tidak terdampak — DB kosong selalu mendapat `device_id` baru.)

### 3.6 (Opsional) Salin konfigurasi `.env`

File `.env` menyimpan kredensial cloud dan tidak boleh ikut ter-commit. Jika perangkat lama sudah punya koneksi cloud, salin file `.env` tersebut ke folder proyek baru. Isinya kira-kira:

```ini
# URL database APLIKASI (default SQLite lokal — biarkan kosong/di-comment)
# APP_DATABASE_URL=sqlite:///essa.db

# URL database CLOUD (Neon) — dipakai skrip backup/sinkronisasi
CLOUD_DATABASE_URL=postgresql+psycopg2://...
```

- Tanpa `.env` → aplikasi tetap berjalan (mode offline murni).
- Dengan `.env` → aplikasi tetap berjalan offline; koneksi cloud tersedia untuk skrip.

### 3.7 Jalankan aplikasi

**Cara paling aman (disarankan): double-click `start_app.bat`** di folder proyek.

Kenapa bukan double-click `main.py`? Di Windows, double-click `main.py` memakai
Python bawaan sistem (sering **versi berbeda** dari `python` di terminal) yang
biasanya **belum punya dependensi cloud (`psycopg2`)** — akibatnya auto-sync
gagal dan tombol SYNC NOW non-aktif (status "CLOUD NONAKTIF", console log
`no module psycopg2`).

`start_app.bat` memakai `python` yang **sama dengan terminal Anda** (yang sudah
terbukti berfungsi), memeriksa `psycopg2` dulu, lalu menjalankan aplikasi. Anda
juga bisa memeriksa lingkungan tanpa membuka aplikasi:

```bash
start_app.bat --check
```

Alternatif (cara manual, sama hasilnya):

```bash
python main.py
```

Pada *first run*, aplikasi otomatis: membuat tabel di `essa.db`, menyinkronkan master tarif penjahit, **menjalankan sinkronisasi dua arah dengan cloud di thread latar** (perangkat baru mengunduh seluruh data; perangkat lama menarik & mengirim perubahan), lalu membuka window utama.

---

## 4. Cara 2 — Instalasi dari Git (clone)

Jika perangkat baru tidak bisa menerima salinan folder (mis. mengambil dari repository):

```bash
git clone <URL-REPOSITORY-ANDA> Essa-Store-App
cd Essa-Store-App
```

Lalu lanjutkan dari **langkah 3.2** di atas. **Perbedaan penting:** karena `*.db` dan `.env` masuk `.gitignore`, keduanya **tidak ikut ter-clone** — Anda harus menyalin `essa.db` (dan `.env` bila ada) secara manual dari perangkat lama.

---

## 5. Verifikasi Instalasi

Setelah `python main.py` berjalan, pastikan:

- [ ] Window terbuka dengan judul **"Yazmina Hijab - Unified Operations Platform"** dan brand **"Yazmina Hijab"** di sidebar kiri.
- [ ] Menu di sidebar: DASHBOARD, CATATAN HARIAN, HUTANG & PELUNASAN, PAYROLL & BON, STOCK MANAGER, INVOICE & PIUTANG, PROFIT SIMULATION, DATA MANAGER.
- [ ] **Dashboard** menampilkan angka (Total Hutang, Piutang, Gaji, Profit) — tanda bahwa data `essa.db` terbaca. Jika semua nol, periksa langkah 3.5.
- [ ] (Jika pakai cloud) Pertama kali dibuka, data muncul otomatis dari cloud — terminal menampilkan `Auto-sync start: ... pull=...`.
- [ ] Coba cetak salah satu PDF (mis. slip gaji atau invoice) untuk memastikan `exports/` dan `assets/` berfungsi.

---

## 6. Update Aplikasi ke Versi Baru

1. Tutup aplikasi.
2. **Backup** dulu `essa.db` (aplikasi otomatis membuatnya di `backups/` saat ditutup — tapi amankan juga secara manual).
3. Ganti file kode dengan versi baru (copy-over folder atau `git pull`).
4. **JANGAN hapus**: `essa.db`, `.env`, folder `backups/`, folder `exports/`.
5. **(Bila versi baru mengubah struktur database)** jalankan migrasi skema ke `essa.db` lokal — sekali saja:
   ```bash
   # Bash (Git Bash): CLOUD_DATABASE_URL dikosongkan agar migrasi memakai essa.db LOKAL
   CLOUD_DATABASE_URL= alembic upgrade head
   # PowerShell:  $env:CLOUD_DATABASE_URL=""; alembic upgrade head
   ```
   Migrasi ini hanya menambah kolom (nullable) — tidak menghapus data. Untuk perubahan skema yang kompleks, ikuti panduan migrasi (`CLOUD_DATABASE_GUIDE.md`).
6. Jalankan `python main.py` kembali.

> ⚠️ `create_all` saat start **hanya membuat tabel yang belum ada** — ia TIDAK menambah
> kolom ke tabel lama. Jadi jika versi baru memakai kolom baru (mis. `updated_at`,
> `created_by_device` / `updated_by_device` dari Fase 6.3), langkah 5 wajib dijalankan
> sekali, kalau tidak aplikasi error `no such column` saat menyimpan data.

---

## 7. Backup & Restore Data

### Backup otomatis
Setiap kali aplikasi ditutup, file `essa.db` otomatis disalin ke folder **`backups/essa_backup_<tanggal-jam>.db`** (30 backup terakhir disimpan).

### Backup manual
```bash
# Di dalam folder proyek (aplikasi TERTUTUP)
cp essa.db backups/essa_backup_manual_$(date +%Y%m%d).db
```

### Restore
1. Tutup aplikasi.
2. Pilih file backup yang diinginkan dari `backups/`.
3. Salin sebagai `essa.db` (timpa yang lama):
   ```bash
   cp "backups/essa_backup_2026-08-01_10-00-00.db" essa.db
   ```
4. **(Jika backup dibuat oleh versi aplikasi lama)** samakan struktur database dengan kode terbaru — sekali saja:
   ```bash
   CLOUD_DATABASE_URL= alembic upgrade head
   ```
   Backup lama mungkin belum punya kolom baru (mis. `updated_at`); tanpa langkah ini aplikasi error `no such column` saat menyimpan data.
5. Jalankan aplikasi kembali.

---

## 8. Pemecahan Masalah (Troubleshooting)

| Gejala | Kemungkinan Penyebab | Solusi |
|---|---|---|
| `No module named 'PySide6'` | Dependensi belum terinstall | `pip install -r requirements.txt` |
| `'python' is not recognized` | Python tidak di PATH | Install ulang Python dengan centang **"Add Python to PATH"**, lalu buka terminal baru |
| Aplikasi terbuka tapi **data kosong / semua nol** (tanpa cloud) | `essa.db` tidak tercopy / salah folder | Pastikan `essa.db` berada di root proyek (sejajar `main.py`); ulangi langkah 3.5-B |
| Aplikasi terbuka tapi **data kosong** (dengan cloud) | Auto-pull tidak berjalan: `.env` tidak tersalin / internet mati saat pertama buka | Pastikan `.env` terisi & jalankan manual: `python -m utils.cloud_sync --pull setup` |
| Error `Failed to connect` saat menjalankan skrip cloud | `CLOUD_DATABASE_URL` kosong/salah di `.env` | Periksa `.env`; atau jalankan skrip cloud tanpa internet/kredensial — **aplikasi utama tidak terpengaruh** |
| `ModuleNotFoundError: psycopg2` | Driver Postgres belum ada di interpreter yang dipakai | `pip install psycopg2-binary` (hanya dibutuhkan untuk skrip cloud) |
| **Double-click `main.py`** → cloud non-aktif, console `no module psycopg2` | Windows membuka `main.py` memakai **Python yang berbeda** (tanpa `psycopg2`) — sedangkan `python main.py` di terminal jalan | Buka aplikasi lewat **`start_app.bat`** (memakai python yang sama dengan terminal), atau jalankan `python main.py` dari terminal; install dependensi di interpreter yang benar: `pip install -r requirements.txt` |
| Console `[CloudSync] GAGAL - ... could not translate host name ... Name or service not known` | Kegagalan **DNS/jaringan SEMENTARA** (mis. Wi-Fi belum siap tepat setelah PC dinyalakan) — hostname Neon sebenarnya valid | **Tidak perlu tindakan**: aplikasi mencoba ulang otomatis (retry) dan data lokal aman. Klik **SYNC NOW** atau buka ulang aplikasi. Bila terus berulang, cek koneksi internet/ISP atau coba `start_app.bat --check` |
| Console `[CloudSync] GAGAL - ... password authentication failed ...` | Password pada `CLOUD_DATABASE_URL` salah/berubah | Perbarui `.env` dengan connection string terbaru dari console Neon (bagian *Connection Details*) |
| Aplikasi langsung tertutup saat start | Ada error di kode/lingkungan | Jalankan `python main.py` dari terminal dan baca pesan error yang muncul |
| PDF invoice tanpa logo | File `assets/images/Logo_Yazmina.png` hilang | Pastikan folder `assets/` ikut disalin |
| Window tidak terbuka / tampilan aneh | Versi PySide6 terlalu lama | Pastikan `PySide6>=6.6.0` terinstall |

---

## 9. File & Folder Penting

| File/Folder | Fungsi | Boleh dihapus? |
|---|---|---|
| `main.py` | Pintu masuk aplikasi | ❌ |
| `start_app.bat` | **Launcher (double-click)** — memakai python yang benar | ❌ |
| `data/`, `ui/`, `utils/` | Kode inti aplikasi | ❌ |
| `assets/` | Logo & aset (dipakai PDF) | ❌ |
| `essa.db` | **Database utama (SEMUA DATA)** | ❌ **WAJIB DIBACKUP** |
| `backups/` | Backup otomatis database | ⚠️ Bisa dibersihkan (otomatis dipangkas) |
| `exports/` | Hasil cetak PDF & Excel | ⚠️ Bisa dibersihkan |
| `.env` | Kredensial cloud (rahasia) | ❌ Jangan di-commit; simpan baik-baik |
| `venv/` | Lingkungan Python (hasil 3.3) | ⚠️ Bisa dibuat ulang |

---

## 10. Catatan Cloud (opsional)

- Aplikasi utama **selalu memakai database lokal** (`essa.db`) dan tidak pernah bergantung pada internet.
- Koneksi cloud (Neon PostgreSQL) saat ini digunakan oleh skrip bantuan: pembuatan skema cloud (`scripts/create_cloud_schema.py`) dan seed data (`scripts/seed_cloud.py`).
- **Sinkronisasi DUA ARAH penuh aktif (Fase 6.2–6.3)**: setiap kali aplikasi **dibuka** dan **ditutup**, perubahan disinkronkan ke cloud (lokal → cloud) dan dari cloud (cloud → lokal) dengan lapisan ID mapping + *last-write-wins* via `updated_at` + delete dua arah + **kepemilikan perangkat** (`created_by_device`/`updated_by_device` — memutuskan baris yang sama vs tabrakan antar perangkat secara pasti). Perangkat baru dengan `.env` terisi otomatis mengunduh seluruh data saat pertama dibuka.
- Manual: `python -m utils.cloud_sync` (dua arah), `--pull setup` (perangkat baru, lokal kosong), `--pull merge` (gabung).
- **Resiliensi jaringan (7 Agu 2026)**: sync mencoba ulang otomatis (hingga 3×) bila gagal
  karena DNS/jaringan sementara; kegagalan dilaporkan dengan pesan ramah dan status sidebar
  menjadi `☁ OFFLINE · SYNC GAGAL` sampai sync berikutnya sukses. Data lokal tidak pernah
  terpengaruh oleh gangguan jaringan — cloud hanya cermin.
- Tanpa cloud, cara memindahkan data ke perangkat baru tetap menyalin `essa.db` (langkah 3.5-B).

---

## Referensi

- `README.md` — gambaran umum proyek & fitur
- `CLOUD_DATABASE_GUIDE.md` — panduan migrasi database ke cloud (Neon) & arsitektur hybrid
- `scripts/` — skrip bantuan migrasi & seed data

---

*Dokumen ini adalah pedoman hidup — perbarui bagian yang berubah seiring perkembangan aplikasi.*
