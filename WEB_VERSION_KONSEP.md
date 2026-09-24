# 🌐 Yazmina Hijab — Web Version (Konsep Rancangan)

> **Status:** Draf Konsep v1.0 · **Tanggal:** 15 Agustus 2026
> **Tujuan:** Rancangan arsitektur, fitur, tampilan, keamanan, dan hosting untuk mengubah aplikasi desktop Yazmina Hijab (Python + PySide6) menjadi aplikasi web yang **fitur & tampilannya sama persis**, hanya diakses lewat browser, dengan **login** agar tidak sembarang orang bisa mengakses.

---

## 1. Ringkasan Eksekutif

Aplikasi desktop **Yazmina Hijab — Unified Operations Platform** adalah sistem operasional bisnis (produksi, hutang, gaji, stok, invoice, profit) berbasis Python + PySide6 dengan tema *cyberpunk industrial*. Versi web bertujuan:

1. **Fitur 1:1** — semua menu, form, tabel, tombol, perhitungan, dan alur kerja dipertahankan persis.
2. **Tampilan identik** — palet warna neon, panel bergaris tajam, tombol uppercase, tetap diterapkan.
3. **Akses via browser** — pengguna membuka URL, login, lalu menggunakan aplikasi dari perangkat mana pun.
4. **Login wajib** — satu akun admin (username + password) sebagai gerbang masuk.

### Keuntungan yang didapat dari versi web

| Aspek | Desktop | Web |
|---|---|---|
| Akses | 1 komputer (instal Python, DB lokal) | Browser apa saja, perangkat mana saja |
| Sinkronisasi multi-perangkat | Perlu mekanisme `cloud_sync` + `sync_id_map` (kompleks) | **Otomatis hilang** — semua perangkat memakai satu database server |
| Backup | SQLite lokal + folder `backups/` | Backup database server (otomatis oleh penyedia/hosting) |
| Distribusi update | Install ulang/manual | Update di server, user langsung dapat versi baru |
| Keamanan data | File `essa.db` bisa dibuka siapa saja di komputer | Dibalut login + HTTPS |

> ⚡ **Penyederhanaan besar:** modul sinkronisasi dua arah (`utils/cloud_sync.py`, `sync_id_map`, `created_by_device`, tombol **SYNC NOW**, indikator cloud di sidebar) **tidak lagi diperlukan** di versi web, karena seluruh perangkat membaca/menulis database terpusat yang sama. Ini menghapus lapisan kompleksitas paling rumit di aplikasi.

---

## 2. Prinsip Desain

1. **Paritas fitur penuh** — tidak ada fitur desktop yang dihilangkan di web.
2. **Identitas visual dipertahankan** — tema cyberpunk industrial adalah "merek" aplikasi; bukan sekadar dark mode biasa.
3. **Kecepatan input** — aplikasi desktop dirancang untuk entri data harian cepat; web harus terasa sama responsifnya (form di atas, tabel di bawah, tombol besar, alur keyboard).
4. **Satu sumber kebenaran data** — database terpusat di server menggantikan SQLite + cloud mirror.
5. **Server-side security** — semua validasi, perhitungan sensitif (uang), dan otorisasi dilakukan di backend; frontend hanya menampilkan & mengirim input.

---

## 3. Arsitektur Teknis

### 3.1 Pilihan Teknologi

| Lapisan | Teknologi | Alasan |
|---|---|---|
| **Backend** | **FastAPI** (Python 3.11+) | Bahasa sama dengan desktop → **model SQLAlchemy & logika bisnis bisa dipakai ulang hampir 100%**; performa tinggi; dokumentasi API otomatis (Swagger). |
| **ORM** | **SQLAlchemy 2.0** | Sudah dipakai desktop; model di `data/models/` dipindahkan & disesuaikan. |
| **Frontend** | **React + Vite** (dengan alternatif Vue) | SPA responsif; mudah membuat tabel interaktif, form dinamis, dan styling custom persis tema desktop. |
| **State/Data fetching** | TanStack Query (React) | Caching, refetch otomatis, dan status loading per halaman. |
| **Auth** | JWT (httpOnly cookie) + bcrypt/argon2 | Satu admin; hash password kuat; cookie aman dari XSS. |
| **PDF** | ReportLab (server) | Engine PDF desktop dipakai ulang, hasilnya dikirim sebagai file download. |
| **Excel** | OpenPyXL + Pandas (server) | Import/export Excel (SKU, tarif, absensi, BigSeller) tetap jalan di server. |
| **Database** | PostgreSQL (VPS) **atau** MySQL/MariaDB (shared hosting) | SQLAlchemy mendukung keduanya; lihat Skenario Hosting. |

### 3.2 Diagram Arsitektur

```
┌─────────────┐      HTTPS/JSON      ┌──────────────────────┐      ┌──────────────┐
│   Browser   │ ◄──────────────────► │   FastAPI (Backend)  │ ◄──► │  Database    │
│ (React SPA) │  login → JWT cookie  │  - API REST          │      │  (Postgres / │
│  theme.css  │                      │  - validasi & logika │      │   MySQL)     │
└─────────────┘                      │  - PDF & Excel engine│      └──────────────┘
                                     │  - session admin     │
                                     └──────────────────────┘
```

### 3.3 Struktur Folder Usulan

```
yazmina-hijab-web/
├── backend/                       # FastAPI
│   ├── app/
│   │   ├── main.py                # Entry FastAPI + mount router
│   │   ├── auth.py                # Login/logout, JWT, dependency "current_admin"
│   │   ├── database.py            # Engine + session (dari data/database.py desktop)
│   │   ├── models/                # ⬅ Dipindahkan & disesuaikan dari data/models/
│   │   ├── schemas/               # Pydantic (request/response per fitur)
│   │   ├── routers/               # API per modul
│   │   │   ├── dashboard.py
│   │   │   ├── harian.py
│   │   │   ├── hutang.py
│   │   │   ├── gaji.py
│   │   │   ├── stok.py
│   │   │   ├── invoice.py
│   │   │   ├── profit.py
│   │   │   └── master.py
│   │   ├── services/              # Logika bisnis (dari logika view desktop)
│   │   └── pdf/                   # pdf_engine.py (adaptasi → response streaming)
│   └── requirements.txt
├── frontend/                      # React + Vite
│   ├── src/
│   │   ├── theme.css              # Tokens tema cyberpunk (dari ui/theme.py)
│   │   ├── components/            # Button, Table, Dialog, FormField, Modal, Tabs
│   │   ├── pages/                 # 1 halaman per menu (8 + login)
│   │   ├── api/                   # Klien fetch untuk tiap modul
│   │   └── App.jsx                # Routing + layout sidebar
└── scripts/
    └── migrate_desktop_to_server.py  # Migrasi data SQLite → server
```

---

## 4. Struktur Aplikasi & Navigasi

### 4.1 Layout Utama (identik dengan desktop)

```
┌──────────┬──────────────────────────────────────────────┐
│ SIDEBAR  │  CONTENT AREA                                │
│ (260px)  │  ┌────────────────────────────────────────┐  │
│          │  │  Header (judul menu + tombol aksi)     │  │
│ YAZMINA  │  ├────────────────────────────────────────┤  │
│ HIJAB    │  │  Konten halaman aktif                  │  │
│ OPERATIONS│ │  (form, tabel, panel, dsb.)            │  │
│ OS v0.8  │  │                                        │  │
│          │  └────────────────────────────────────────┘  │
│ ──────── │                                             │
│ DASHBOARD│                                             │
│ CATATAN  │                                             │
│  HARIAN  │                                             │
│ HUTANG & │                                             │
│ PELUNASAN│                                             │
│ PAYROLL &│                                             │
│  BON     │                                             │
│ STOCK    │                                             │
│ MANAGER  │                                             │
│ INVOICE &│                                             │
│ PIUTANG  │                                             │
│ PROFIT   │                                             │
│ SIMULATION│                                             │
│ DATA     │                                             │
│ MANAGER  │                                             │
│ ──────── │                                             │
│ 👤 admin │                                             │
│ LOGOUT   │                                             │
└──────────┴──────────────────────────────────────────────┘
```

**Pemetaan navigasi desktop → web:**

| Sidebar Desktop | Halaman Web (route) | Catatan Perubahan |
|---|---|---|
| DASHBOARD | `/dashboard` | Sama persis. |
| CATATAN HARIAN | `/harian` | Sama persis (4 tab). |
| HUTANG & PELUNASAN | `/hutang` | Sama persis (2 tab). |
| PAYROLL & BON | `/gaji` | Sama persis (4 tab). |
| STOCK MANAGER | `/stok` | `os.startfile` → download Excel. |
| INVOICE & PIUTANG | `/invoice` | PDF dibuka di tab baru / download. |
| PROFIT SIMULATION | `/profit` | Sama persis. |
| DATA MANAGER | `/master` | Sama persis (4 tab); upload file → `input type=file`. |
| ☁ SYNC NOW + indikator cloud | **DIHAPUS** | Tidak relevan — database terpusat. |
| EXIT SYSTEM | **LOGOUT** | Kembali ke halaman login (hapus session). |

> Setiap menu tetap **lazy-load**: halaman hanya dirender/diminta ke server saat tombol diklik (meniru perilaku `switch_page()` desktop), dan data di-refetch otomatis saat pindah halaman.

---

## 5. Desain UI/UX Global

### 5.1 Design Tokens (salinan persis dari `ui/theme.py`)

| Token | Nilai Hex | Penggunaan |
|---|---|---|
| `--bg-void` | `#090A0F` | Latar utama & input |
| `--bg-panel` | `#161925` | Panel/blok grid |
| `--text-main` | `#E0E0E0` | Teks utama |
| `--text-muted` | `#8B93A5` | Label/placeholder |
| `--neon-cyan` | `#00F0FF` | Aksi utama, fokus |
| `--neon-pink` | `#FF003C` | Danger/delete |
| `--neon-yellow` | `#FCE205` | Warning/pending |
| `--border-dim` | `#2A2E45` | Garis grid |

**Aturan gaya (dari QSS desktop):**
- ✅ **Sudut tajam** (`border-radius: 0`) untuk tombol, panel, input — tidak ada sudut membulat di komponen utama.
- ✅ Tombol: transparan + border cyan, teks **uppercase**, `letter-spacing: 1px`, bold; hover → latar cyan + teks hitam; varian danger (pink) & solid-cyan.
- ✅ Panel: latar `#161925`, border `#2A2E45`, tanpa bayangan lembut.
- ✅ Input: latar void, border dim, teks cyan saat fokus; spinbox dengan panah segitiga tajam.
- ✅ Font: `Segoe UI / Roboto / Consolas` (fallback sistem), ukuran ~10pt.
- ✅ Tabel: header huruf kapital, teks angka rata kanan, status berwarna (hijau LUNAS, kuning PARTIAL, merah OPEN, cyan kode batch).
- ✅ Kartu KPI: border kiri 4px aksen warna + nilai besar (22pt) rata kanan.

### 5.2 Komponen Web (padanan Qt)

| Komponen Desktop | Komponen Web |
|---|---|
| `CyberButton` | `<Button>` (4 varian: default, danger, solid-cyan, solid-yellow) |
| `CyberTable` (`QTableWidget`) | `<DataTable>` (kolom, sort, multi-select via checkbox/CTRL, sticky header) |
| `QTabWidget` | `<Tabs>` (tab aktif: border-bawah 2px cyan) |
| `QMessageBox` (warning/info/question/critical) | `<Dialog>` / `<ConfirmDialog>` / `<Toast>` (ikon sama) |
| `QDateEdit` kalender popup | `<input type="date">` |
| `QComboBox` + completer | `<Combobox>` dengan pencarian (filter contains, case-insensitive) |
| `QDoubleSpinBox` | `<NumberInput>` (prefix "Rp ", read-only variant) |
| `QGroupBox` | `<Panel>` dengan judul aksen |
| Notifier `database_changed` (Signal) | TanStack Query `invalidateQueries()` → semua halaman refetch |

### 5.3 Perilaku penting yang dipertahankan

- **Search global** per halaman (Harian & Hutang) dengan **debounce 300ms**, filter case-insensitive per tab aktif.
- **Auto-hitung** total (qty × harga) real-time di form offline & hutang.
- **Auto-fill** sisa qty distribusi saat memilih batch cutting.
- **Mode edit** saat baris dipilih: tombol berubah teks (`SIMPAN CUTTING` → `UPDATE CUTTING`), tombol `BATAL EDIT` & `HAPUS` muncul.
- **Multi-select** (CTRL/SHIFT) untuk pelunasan hutang batch & pilih penjualan invoice.
- **Konfirmasi sebelum hapus** (termasuk peringatan cascade: hapus cutting = distribusi terkait ikut terhapus).
- **Soft delete** (`is_deleted = 1`) — bukan hapus fisik, konsisten dengan desktop.

---

## 6. Spesifikasi Halaman per Menu

> Setiap halaman di bawah ini adalah **paritas penuh** dari view desktop. Format: struktur → form → tabel → aksi → aturan bisnis kunci.

### 6.1 `/login` — Halaman Login (baru)

- Layout: panel tengah bergaya cyberpunk (brand "YAZMINA HIJAB" cyan besar, sub "OPERATIONS OS · WEB", garis grid dekoratif).
- Form: `Username` + `Password` (masked) + tombol **MASUK**.
- Pesan error merah (neon-pink) bila kredensial salah; indikator loading saat submit.
- Setelah sukses → redirect ke `/dashboard`.
- Tanpa login: semua route selain `/login` diblokir (lihat Bagian 7).

### 6.2 `/dashboard` — Dashboard

**Struktur (identik desktop):**
- Header: judul "Dashboard Yazmina Hijab" (26pt cyan bold) + tombol **↻ REFRESH**.
- Panel filter rentang: tombol **HARI INI** · **MINGGU INI** · **BULAN INI** · input `Dari:` / `Sampai:` (date) · **TERAPKAN**.
- Label periode aktif: `Periode aktif (Gaji & Profit): YYYY-MM-DD s/d YYYY-MM-DD`.
- Grid 2×2 KPI card (border-kiri aksen 4px):

| Card | Aksen | Warna Nilai |
|---|---|---|
| TOTAL HUTANG TERSISA | Pink | Pink |
| TOTAL PIUTANG | Kuning | Kuning |
| GAJI KARYAWAN | Cyan | Cyan |
| PROFIT PRODUKSI | Cyan | Hijau `#69F0AE` bila ≥ 0, Pink bila rugi |

- Catatan kaki (9pt muted): *"Hutang & Piutang menampilkan saldo terkini (tidak terpengaruh filter tanggal). Filter berlaku untuk Gaji Karyawan & Profit Produksi."*
- Format angka: `Rp 1.234.567` (titik ribuan).

**API yang dipakai:** `GET /api/dashboard?mulai=&akhir=` → 4 nilai (pakai ulang fungsi `data/dashboard_queries.py`).

### 6.3 `/harian` — Catatan Harian (4 tab)

Header: judul + search bar `🔍 Cari data...` (debounce 300ms, memfilter tabel tab aktif).

**Tab 1 — HASIL CUTTING**
- Form: Tanggal · Sumber Kain (Pilih Batch) · SKU Produk (dengan pencarian) · Qty Hasil Potong · **[SIMPAN CUTTING]** · [BATAL EDIT] · [HAPUS].
- Tabel: `ID | Tanggal | Kode Batch | SKU | Qty`.
- Aturan: dropdown *Sumber Kain* diisi `DebtEntry` tipe `MODAL` dengan `status_cutting = OPEN` (format `[kode_batch] keterangan (Rp …)`); saat simpan, `kode_produksi` diambil otomatis dari hutang modal terpilih.
- Hapus → konfirmasi: *"Distribusi Jahit yang terkait dengan cutting ini TURUT DIHAPUS"* (soft delete cascade).

**Tab 2 — DISTRIBUSI JAHIT**
- Form: Tanggal · Penerima (Penjahit/Pengsup) · Filter Kode Batch · List Batch Cutting · Qty Diambil · **[SIMPAN DISTRIBUSI]**.
- Tabel: `ID | Tanggal | Penerima | Jenis | Kode Batch | SKU | Qty`.
- Aturan: list batch cutting menampilkan **sisa** (`Nama (Sisa X Pcs)`) = qty cutting − qty terdistribusi; memilih batch otomatis mengisi Qty dengan sisa (bisa diedit manual); dropdown `Filter Kode Batch` mengubah daftar list cutting.

**Tab 3 — PENGELUARAN OFFLINE**
- Form: Tanggal · Pembeli (Person KLIEN/LAINNYA/SUPPLIER + data Client) · SKU · Qty (desimal 2) · Harga Satuan · **Total (auto, read-only)** · **[SIMPAN PENJUALAN]**.
- Tabel: `ID | Tanggal | Pembeli | SKU | Qty | Harga | Total`.
- Aturan: `Total = Qty × Harga` real-time; setelah simpan, **sinkronisasi otomatis** `ClientReceivable` (total tagihan = Σ penjualan aktif, sisa = tagihan − Σ pembayaran, status LUNAS/OPEN); pembeli mendukung Person lama & Client baru (prefix `CLIENT_`).

**Tab 4 — MODAL OPERASIONAL**
- Form: Tanggal · Jenis (`OVERHEAD | BARANG | UTILITAS | LAINNYA`) · Keterangan · Nominal Total · **[SIMPAN PENGELUARAN]**.
- Tabel: `ID | Tanggal | Kategori | Keterangan | Nominal/Total` (kolom keterangan fleksibel).

### 6.4 `/hutang` — Hutang & Pelunasan (2 tab)

Header: judul + search bar (debounce, filter per tab).

**Tab 1 — BARANG TERHUTANG**
- Hint pink: *"TAHAN CTRL atau SHIFT untuk memilih banyak hutang sekaligus!"*
- Tabel (multi-select): `ID | Tgl Ambil | Supplier | SKU | Qty | Total Hutang | Terbayar | Status` (Status merah OPEN / hijau LUNAS).
- Panel kiri — *CATAT HUTANG BARU*: Tanggal · Supplier · SKU · Qty/Jumlah · Harga Satuan · Total Hutang (auto) · [SIMPAN BARU] · [RESET] · [HAPUS].
- Panel kanan — *PILIH HUTANG UNTUK MELUNASI*: Tgl Bayar · Nominal (otomatis diisi = Σ sisa baris terpilih, bisa diedit) · **[BAYAR / CICIL SEMUA]** · [BATAL LUNAS (SET OPEN)].
- Aturan: nominal dibagi ke baris terpilih secara berurutan (FIFO baris); hanya boleh 1 supplier dalam satu batch; selesai → **PDF Nota** (`generate_batch_receipt_pdf`); BATAL LUNAS menghapus riwayat pembayaran & set OPEN.

**Tab 2 — MODAL HUTANG**
- Tabel: `ID | Tgl Hutang | Pemberi Modal | Kode Batch | Keterangan | Total Hutang | Deposit/Lunas | Status`.
- Panel kiri — *CATAT PINJAMAN MODAL*: Tanggal · Pemberi Modal · **Kode Batch** (auto-generate `PRD-MMYY-XXX`, bisa diedit) · Jenis/Ket (`Kain Jersey | Label Akrilik | Hangtag | Modal Tunai | Lainnya`, editable) · Qty · Harga · Total (auto) · tombol simpan/reset/hapus.
- Panel kanan — *PILIH PINJAMAN UNTUK DEPOSIT*: Tgl Deposit · Nominal · **[SETOR DEPOSIT SEMUA]** · [BATAL LUNAS (SET OPEN)] + **PDF Nota**.
- Aturan: kode produksi otomatis = urutan terakhir bulan ini +1; baris MODAL `OPEN` menjadi sumber dropdown *Sumber Kain* di menu Harian.

### 6.5 `/gaji` — Payroll & Bon (4 tab)

**Tab 1 — GAJI PENJAHIT**
- Top: Nama Penjahit · Tanggal · Sisa Bon Lama (read-only, pink) · +Tambah Bon Baru · −Potong Bon Minggu Ini.
- Mid: Pilih SKU/Jenis (dari `MasterTarifPenjahit` aktif) · Qty · Harga/Pcs (auto dari master) · **[TAMBAH GARAPAN]** · **[IMPORT EXCEL]** · **[EXPORT FORMAT]**.
- Keranjang: `Jenis Garapan | Qty | Harga Satuan | Total Harga` + tombol Hapus Baris.
- Bottom: label **TOTAL KOTOR: Rp …** (kuning) + **[SIMPAN GAJI PENJAHIT]** (solid cyan).
- Aturan: simpan → `SalaryRun` (tipe `BORONGAN_PENJAHIT`) dengan **dedup per person+tanggal** (update, bukan duplikat); tulis `SalaryLineItem` + `BonMovement` (TAMBAH/POTONG_GAJI) + update `BonBalance`; validasi *potong ≤ bon lama* dan *potong ≤ gaji kotor*; langsung **generate PDF slip gaji** (download).
- ⚙️ **Replikasi startup-sync desktop:** `main.py` desktop otomatis menyinkronkan `TarifMaster.tarif_jahit > 0` → `MasterTarifPenjahit` (kode_garapan = kode_sku) saat aplikasi dibuka. Di web, perilaku ini harus direplikasi — misalnya dijalankan otomatis **setelah import tarif** dan **di skrip migrasi data**, agar dropdown Garapan Penjahit tidak pernah kosong.
- Import Excel: kolom SKU/Garapan & Qty (harga diambil dari master bila kosong).

**Tab 2 — TOTALAN PENGSUP**
- Top: Nama Pengsup · Tanggal · Sisa Bon Lama · +Tambah Bon · −Potong Kasbon · **PENGURANG (RAW MATERIAL)**: Qty Kain Mentah · Harga Kain/Kg.
- Mid: Tipe Setoran (`Setor Barang Jadi (Kain) | Setor Potongan (Pcs) | Potongan Kain Mentah (Kg)`) · SKU · Qty · Harga/Unit (auto-cerdas dari `TarifMaster`, dengan fallback base-size) · **[TAMBAH KE DAFTAR]** · [IMPORT/EXPORT Excel].
- Kiri bawah — *CATATAN NOTA & OPERASIONAL*: catatan manual + tombol import/export.
- Kanan bawah — *SUMMARY PERHITUNGAN FINANSIAL*: Total Pemasukan Barang/Potongan · −Potongan Harga Kain Mentah · **TOTAL DITERIMA (SBLM KASBON)** · **GAJI BERSIH (NETT)** · **[SIMPAN REKAP PENGSUP]**.
- Aturan: rumus `gaji_kotor = barang_jadi − kain_mentah + jasa_potongan`; `[KAIN_MENTAH]` & prefix `[BARANG]/[POTONG]` disimpan sebagai `SalaryLineItem`; dedup per person+tanggal; PDF slip.

**Tab 3 — GAJI KARYAWAN (ABSENSI)**
- Top: **[IMPORT EXCEL ABSENSI]** · [EDIT DATA ABSENSI & GAJI] · label file · Tgl Payroll · **Tarif Normal** (default Rp 150/mnt) · **Tarif Lembur** (default Rp 160/mnt).
- Grid (11 kolom, kolom ID disembunyikan): `ID | Nama Karyawan | Hadir | Menit Normal | Tarif Normal | Menit Lembur | Tarif Lembur | Gaji Kotor | Bon Lama | Potong Kasbon | Gaji Bersih`.
- Edit: klik baris → tombol **EDIT DATA ABSENSI & GAJI** membuka editor per karyawan (tabel rincian harian: Tanggal, Jam Masuk, Jam Keluar, Menit Normal, Menit Lembur; + tarif normal/lembur, potongan kasbon; tombol **HITUNG ULANG & TERAPKAN** / **BATAL**).
- Bottom: hint tips edit · [KOSONGKAN TABEL] (pink) · **[SIMPAN & CETAK SEMUA SLIP]** (solid cyan → PDF batch `generate_batch_karyawan_slip`).
- Aturan: perhitungan menit/lembur konsisten dengan desktop; simpan `SalaryRun` tipe `PASUKAN_KARYAWAN` + `AttendanceRecord` + update bon.

**Tab 4 — KASBON / UTANG (sub-tab ganda)**
- **DASHBOARD KASBON**: tabel `ID Person | Nama Personel | Tipe Personel | Sisa Kasbon` (saldo > 0, nilai magenta) + [🔄 REFRESH DATA BON].
- **UPDATE BON MANUAL**: pilih nama (PENJAHIT/PENGSUP/KARYAWAN) → Sisa Saldo Saat Ini (16pt pink) · Jenis Tindakan (`+ TAMBAH BON BARU | − POTONG BON (BAYAR TUNAI)`) · Nominal · Keterangan · **[SIMPAN UPDATE BON]**; tabel riwayat `Tanggal | Jenis | Sumber | Keterangan | Nominal` (warna kuning TAMBAH / hijau POTONG).
- Aturan: potong tidak boleh melebihi saldo; tulis `BonMovement` (`TAMBAH_MANUAL`/`POTONG_MANUAL`, sumber `MANUAL: …`).

### 6.6 `/stok` — Stock Manager

- Header: "INVENTORY & BIGSELLER SYNC".
- Hanya **satu tab** (desktop memakai `QTabWidget` dengan 1 tab): **STAGING & EXPORT (BIGSELLER)** — bukan menu bertab:
  - Form: Pilih SKU (pencarian) · Qty · Harga Satuan (opsional) · **[TAMBAHKAN KE STAGING]**.
  - Tabel staging: `Kode SKU | Jumlah | Harga Satuan | Status` (status "Siap Export" cyan).
  - Aksi: [HAPUS BARIS] (pink) · **[EXPORT PENAMBAHAN (IN)]** (cyan) · **[EXPORT PENGURANGAN (OUT)]** (kuning).
- Aturan: export IN = file `.xlsx` kolom `*Nomor SKU (SKU atau GTIN Wajib Diisi) | *GTIN | *Jumlah Penambahan Stok | Harga Satuan | Tanggal Produksi | Tanggal Kedaluwarsa`; export OUT = `*Nomor SKU | *Jumlah Pengurangan Stok`. File dinamai `Penambahan_Stok_YYYYMMDD.xlsx` / `Pengurangan_Stok_YYYYMMDD.xlsx`. Download otomatis dari browser.

### 6.7 `/invoice` — Invoice & Piutang

- Header + [REFRESH DATA]; dropdown **Pilih Klien** (dari `Client` + `Person` legacy yang punya transaksi/piutang; label `(Person)` untuk legacy).
- Info: *"PILIH BARIS PENJUALAN (centang) untuk cetak invoice — deposit diisi di bawah"*.
- Tabel transaksi gabungan: `ID | Tanggal | Keterangan | Debit (Rp) | Kredit (Rp) | Sisa (Rp) | Status` — penjualan (debit, pink) + pembayaran (kredit, hijau) diurutkan per tanggal, **status FIFO** (LUNAS hijau / PARTIAL kuning / BELUM LUNAS merah), sisa = running balance.
- Ringkasan (panel bawah): Total Tagihan (pink) · Total Dibayar (hijau) · Sisa Piutang (16pt merah/hijau) · Status (LUNAS/BELUM LUNAS).
- Opsi invoice: **Deposit (Rp)** · **Diskon (Rp)** · Tgl Dep · **Jatuh Tempo** (default +30 hari) · Metode (`TUNAI | TRANSFER`).
- Aksi: **[CETAK INVOICE PDF]** (solid cyan, aktif jika ada penjualan terpilih) · **[HAPUS PEMBAYARAN]** (pink, aktif jika baris pembayaran terpilih).
- Aturan: memilih baris penjualan → total tagihan terpilih tampil di label; deposit > 0 → konfirmasi "Simpan deposit? YA=simpan pembayaran baru / TIDAK=cetak ulang saja"; simpan `ClientReceivablePayment` + recalculate receivable (self-healing); PDF invoice (`generate_invoice_pdf`) dengan data klien (nama, alamat, telp) + diskon + jatuh tempo; hapus pembayaran = undo + recalculate.

### 6.8 `/profit` — Profit Simulation

- Header: "REAL-TIME PROFIT ANALYZER" (center).
- **Pilih Kode Produksi** (dropdown, auto-analisis saat dipilih).
- Panel kiri — *DATA MODAL BAHAN (Hutang Modal)*: Total Qty Kain (Kg) · Harga Beli/Kg · **Total Modal Bahan** (pink 14pt) · Status Kain (`FULL CUTTING ✓` hijau / `BELUM FULL (Masih Sisa)` kuning) · tombol **TANDAI KAIN HABIS (FULL CUT)** / **BATALKAN FULL CUT (BUKA LAGI)** (toggle `status_cutting`).
- Panel kanan — *DATA PRODUKSI & DISTRIBUSI*: Total Hasil Cutting (Pcs) · Distribusi Penjahit (Home) · Distribusi Peng-sup · Status Verifikasi (merah "Belum Di-Cutting!" / kuning "Tertahan (Kurang X pcs)" / hijau "Siap Dihitung ✓").
- Panel bawah — *LAPORAN LABA BERSIH (NET PROFIT)*: A. Estimasi Pendapatan (Omzet) · B. Gross Margin (Pendapatan − Modal Kain) · C. Beban Produksi Home (Sesuai SKU) · D. Beban Produksi Supplier (Sesuai SKU) · **LABA BERSIH (NET PROFIT)** 24pt (hijau `#69F0AE` / merah `#ff5252`).
- Aturan (kunci): konstanta biaya `PACK 100 · HANGTAG 97 · WOVEN 150 · HTROPE 20 · THREAD 100 · AKRILIK 250` (akrilik hanya SKU base `DG`); ongkos jahit/potong dicari dari `TarifMaster` dengan fallback base-size → base → default (700/1500); SKU tanpa harga jual → info "Harga Kosong" (pendapatan Rp 0); hasil **disimpan ke `profit_history`** (upsert per batch → dipakai Dashboard); verifikasi distribusi < cutting → non-blocking warning, simulasi tetap tampil.

### 6.9 `/master` — Data Manager (4 tab)

**Tab 1 — MASTER SKU**
- Tabel: `ID | Kode SKU | Nama Produk | Harga Modal` + editor (Kode · Nama · Modal) + [SIMPAN SKU] · [RESET] · [HAPUS SKU] (disable saat tidak ada baris terpilih).
- Aturan: hapus ditolak dengan pesan jika SKU dipakai tabel lain (FK protection).

**Tab 2 — DIRECTORY PERSONS**
- Tabel: `ID | Nama Person | Tipe Kategori | Status` + editor (Nama Lengkap · Tipe `KARYAWAN | PENJAHIT | PENGSUP | KLIEN | SUPPLIER | LAINNYA`) + tombol simpan/reset/hapus.
- Aturan: hapus ditolak jika person punya riwayat Bon/Gaji/Hutang (proteksi pembukuan).

**Tab 3 — KLIEN**
- Tabel: `ID | Nama Klien | No. HP | Alamat` + form CRUD + [REFRESH].

**Tab 4 — IMPORT EXCEL**
- Section *IMPORT MASTER SKU*: pilih file `MasterSKU.xlsx` (sheet "Master SKU"; kolom Nomor SKU, Judul, Rata-Rata Modal Bobot) → **[MULAI IMPORT SKU]** → hasil `✅ X SKU berhasil diimport. Y baris dilewati.`
- Section *IMPORT MASTER TARIF*: pilih `Master_tarif.xlsx` (sheet `SKU_Pengsup` + `SKU_Penjahit`) → **[MULAI IMPORT TARIF]** → hasil serupa.
- **LOG ERROR** (panel merah, scroll) menampilkan baris gagal.
- Aturan: upload file via browser; logika import dipakai ulang dari `data/excel_importer.py`.

---

## 7. Sistem Autentikasi (Satu Admin)

### 7.1 Kebutuhan
- **Satu akun admin**: `username` + `password`.
- Semua akses di luar halaman login harus diautentikasi.

### 7.2 Desain

| Aspek | Keputusan |
|---|---|
| Penyimpanan kredensial | Tabel `admin_users` di database server (hash password) — bukan hardcode di kode |
| Hash password | `bcrypt` atau `argon2` (salt otomatis) |
| Mekanisme session | **JWT** disimpan di **httpOnly cookie** (aman dari JavaScript/XSS) |
| Masa berlaku | 8–12 jam, refresh otomatis saat aktif; cookie `Secure` + `SameSite=Lax` |
| Proteksi | Rate limit login (mis. 5 percobaan/menit → blokir sementara), input sanitasi, HTTPS wajib |
| Setup awal | Script `create_admin.py` — membuat akun admin pertama (wajib dijalankan saat deploy) |
| Logout | Hapus cookie → kembali ke `/login` |

### 7.3 Alur

```
Browser ──POST /api/auth/login──► FastAPI
   │ username+password             │ bcrypt.compare
   │                               ▼
   │ ◄── set-cookie: token=JWT ── OK / 401
   ▼
Browser ──GET /api/dashboard──► FastAPI
   │ cookie token                  │ verify JWT
   │                               ▼
   │ ◄── data ───────────────── OK / 401 → redirect /login
```

- Dependency FastAPI `require_admin` melindungi **seluruh router**; tanpa token valid → `401` → frontend redirect ke `/login`.
- Halaman login di-frontend diproteksi sebaliknya: jika cookie valid, redirect ke `/dashboard`.

---

## 8. Database & Migrasi Data

### 8.1 Strategi
- **Model SQLAlchemy dipakai ulang** dari `data/models/` (26 tabel) — penyesuaian kecil: tipe `String` tanggal sudah cocok untuk Postgres/MySQL; `Computed("UPPER(nama)")` di `Person` perlu penyesuaian sintaks per DB.
- **Tabel baru:** `admin_users` (auth).
- **Tabel yang tidak lagi diperlukan:** `sync_id_map` (jika ada di skema cloud), kolom `created_by_device`/`updated_by_device` boleh dipertahankan (tidak berbahaya) atau di-drop.

### 8.2 Migrasi Data Desktop → Server

1. Ekspor data dari SQLite desktop (`essa.db`).
2. Jalankan skrip `scripts/migrate_desktop_to_server.py`:
   - Baca semua tabel dari SQLite (SQLAlchemy).
   - Tulis ke database server dengan urutan induk → anak (SKU → Person/Client → transaksi → pembayaran).
   - Pertahankan relasi FK & nilai `is_deleted`/status.
3. Verifikasi jumlah baris (skrip pembanding, seperti `scripts/_verify_all_counts.py` yang sudah ada).
4. **Opsional:** jika desktop sudah memakai cloud Neon, data bisa langsung di-pull dari cloud sebagai sumber migrasi.

### 8.3 Catatan data
- Format tanggal di desktop adalah string `YYYY-MM-DD` — dipertahankan agar logika query (`between`, dll.) tetap sama.
- Angka uang memakai `Float` (konsisten dengan desktop). **Rekomendasi lanjutan:** migrasi bertahap ke `Numeric(18,2)` untuk presisi uang (bisa jadi fase perbaikan terpisah).

---

## 9. Export & Import (PDF / Excel)

| Fungsi Desktop | Implementasi Web |
|---|---|
| Slip gaji penjahit/pengsup (`generate_salary_slip`) | Backend generate PDF → `FileResponse` → browser download/buka tab baru |
| Slip batch karyawan (`generate_batch_karyawan_slip`) | Sama; file digabung 1 PDF |
| Invoice (`generate_invoice_pdf`) | Sama; dibuka di tab baru + tombol simpan |
| Nota pelunasan (`generate_batch_receipt_pdf`) | Sama |
| Export Excel BigSeller (IN/OUT) | Backend generate `.xlsx` → download |
| Export format garapan (penjahit/pengsup) | Backend template `.xlsx` → download |
| Import Excel (SKU, tarif, absensi, garapan) | `<input type="file">` → upload → backend parse (OpenPyXL/Pandas, pakai ulang `excel_importer.py`) → hasil + log error |

> Nama file PDF di desktop menyertakan timestamp — dipertahankan (mis. `Slip_Gaji_..._20260815.pdf`).

---

## 10. Skenario Hosting (Dua Rancangan)

### Skenario A — VPS / Cloud VM (Rekomendasi Utama)

**Contoh penyedia:** DigitalOcean, Vultr, Contabo, Hostinger VPS, AWS Lightsail. Biaya ~$5–12/bulan.

**Arsitektur:**
```
Internet → (DNS) → Nginx/Caddy (HTTPS, reverse proxy) → FastAPI (Uvicorn/Gunicorn)
                                                          └── PostgreSQL
```
- **Database:** PostgreSQL (atau Neon serverless — bisa langsung sambung ke cloud yang sudah ada).
- **Proses:** Gunicorn + Uvicorn workers; dikelola PM2 atau systemd; restart otomatis.
- **HTTPS:** Caddy (otomatis) atau Nginx + Let's Encrypt.
- **Update deploy:** `git pull` + `systemctl restart` (atau Docker Compose).
- **Backup:** `pg_dump` terjadwal (cron) + snapshot provider; restore mudah.
- **Keunggulan:** bebas total, performa penuh, mudah scaling, FastAPI berjalan native.

**Langkah deploy ringkas:**
1. Sediakan VPS (Ubuntu 22.04/24.04, minimal 1 vCPU/1–2 GB RAM).
2. Install Python 3.11+, PostgreSQL, Nginx/Caddy.
3. Clone repo `yazmina-hijab-web`, buat venv, `pip install -r requirements.txt`.
4. Set `.env` (DATABASE_URL, SECRET_KEY, dll.), jalankan migrasi + `create_admin.py`.
5. Jalankan Gunicorn; konfigurasi reverse proxy + HTTPS; pasang SSL.
6. Uji akses dari browser.

---

### Skenario B — Shared Hosting (cPanel)

**Contoh penyedia:** Hostinger, Niagahoster. Biaya ~Rp 30–80rb/bulan.

**Keterbatasan & solusi:**

| Keterbatasan | Solusi |
|---|---|
| Python tidak selalu tersedia | Pilih paket **Hostinger Premium/Cloud** yang mendukung **Python App (Passenger)**; atau gunakan **App Server (Node)** sebagai alternatif. |
| PostgreSQL jarang ada | Gunakan **MySQL/MariaDB** (selalu tersedia) — SQLAlchemy tinggal ganti `DATABASE_URL` (`mysql+pymysql://…`); query string tanggal & agregat harus dicek ulang. |
| Tidak bisa pasang Nginx | Passenger otomatis menjalankan aplikasi; HTTPS disediakan panel (AutoSSL). |
| Proses latar / cron terbatas | Backup manual via phpMyAdmin/panel; atau jalankan backup terjadwal dari server lain/VPS kecil. |
| Koneksi DB lambat (remote) | MySQL di hosting yang sama dengan app → koneksi lokal cepat. |

> ⚙️ **Penting (ASGI vs WSGI):** FastAPI adalah aplikasi **ASGI**, sedangkan Passenger umumnya mengekspos **WSGI**. Jangan memanggil app FastAPI langsung dari `passenger_wsgi.py` — bungkus dulu dengan adapter `a2wsgi` (contoh: `from a2wsgi import WSGIMiddleware; application = WSGIMiddleware(app)`), atau jalankan Uvicorn pada port internal dan arahkan Passenger sebagai reverse proxy.

**Struktur cPanel:**
```
public_html/
├── passenger_wsgi.py   # Entry WSGI → bungkus app FastAPI dengan a2wsgi
├── backend/            # Kode FastAPI (di luar public_html lebih aman, bila bisa)
└── frontend/           # build statis React (dist) → dilayani sebagai file statis
```

> ⚠️ **Catatan penting:** shared hosting biasanya **tidak mendukung WebSocket/SSE**, dan batas waktu eksekusi request ketat — frontend harus polling/refetch biasa (bukan real-time push). Untuk aplikasi ini (entri data harian) itu sangat cukup.

**Kesimpulan pemilihan:**
| Kriteria | VPS | Shared Hosting |
|---|---|---|
| Kemudahan setup | Sedang | Mudah (panel) |
| Dukungan Python & Postgres | ✅ Penuh | ⚠️ Bergantung penyedia |
| Biaya | $5–12/bln | Rp 30–80rb/bln |
| Performa & kontrol | Tinggi | Rendah–sedang |
| Rekomendasi | **✅ Utama** | Alternatif hemat (cek dukungan Python Passenger) |

---

## 11. Keamanan

1. **HTTPS wajib** di semua skenario (SSL panel / Let's Encrypt).
2. **Login:** rate-limit, hash bcrypt/argon2, JWT httpOnly cookie, logout.
3. **Otorisasi:** dependency `require_admin` di seluruh API server-side (bukan sekadar sembunyikan tombol di UI).
4. **Validasi input** di backend (Pydantic): tipe angka, rentang, string bersih — mencegah injeksi & nilai negatif pada uang.
5. **SQL injection:** SQLAlchemy parameterized queries (sudah bawaan).
6. **CSRF:** proteksi untuk mutasi (cookie `SameSite=Lax` + token bila diperlukan).
7. **XSS:** framework React men-escape otomatis; hindari `dangerouslySetInnerHTML`.
8. **Data sensitif:** `.env` tidak masuk git; `SECRET_KEY` kuat & unik.
9. **Backup:** terjadwal (VPS: `pg_dump`; shared: export panel) + uji restore.
10. **Audit dasar:** log login sukses/gagal (bisa tampil di dashboard admin).

---

## 12. Roadmap Implementasi (Fase)

| Fase | Isi | Output |
|---|---|---|
| **Fase 0 — Fondasi** | Setup repo monorepo, FastAPI + React skeleton, tema cyberpunk CSS, halaman login + auth JWT | App bisa login/logout, dashboard kosong |
| **Fase 1 — Data & Master** | Migrasi model + database, API & halaman `/master` (SKU, Person, Client, Import Excel) | Master data CRUD jalan di browser |
| **Fase 2 — Catatan Harian** | API & halaman `/harian` (4 tab, dropdown dinamis, auto-hitung, soft delete) | Entri harian harian berfungsi |
| **Fase 3 — Hutang & Pelunasan** | `/hutang` (2 tab, multi-select, batch payment, batal lunas, PDF nota) | Alur hutang lengkap |
| **Fase 4 — Payroll & Bon** | `/gaji` (4 tab: penjahit, pengsup, absensi, kasbon) + import/export Excel + PDF slip | Payroll lengkap |
| **Fase 5 — Invoice & Stock** | `/invoice` (tabel FIFO, deposit, PDF invoice) + `/stok` (staging & export BigSeller) | Transaksi penjualan & ekspor jalan |
| **Fase 6 — Profit & Dashboard** | `/profit` (analisis batch, full cut, profit_history) + `/dashboard` (KPI + filter) | Laporan profit & dashboard jalan |
| **Fase 7 — Migrasi Data & UAT** | Skrip migrasi SQLite→server, verifikasi jumlah baris, uji paritas fitur 1:1 | Data produksi aman di server |
| **Fase 8 — Deploy & Hardening** | Deploy sesuai skenario hosting terpilih, HTTPS, backup, uji dari perangkat lain | Go-live |

**Kriteria "selesai" setiap fase:** setiap fitur desktop di fase tersebut dapat dilakukan **end-to-end** lewat browser, hasil database identik dengan desktop.

---

## 13. Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| Fitur kompleks (distribusi sisa qty, FIFO piutang, rumus profit) salah porting | Porting per fase + tabel perbandingan data (skrip verifikasi jumlah & nilai) |
| Perbedaan perilaku query tanggal Postgres/MySQL vs SQLite | Migration test awal; adopsi `Date` column bila perlu |
| Shared hosting tidak dukung Python | Cek dukungan Passenger sebelum beli; fallback VPS |
| PDF tampil beda di web | PDF dirender server (ReportLab) → byte-identical; browser hanya menampilkan file |
| Angka Float kurang presisi untuk uang | (Opsional) migrasi bertahap ke `Numeric(18,2)` |
| Kecepatan input turun karena network | Optimasi: prefetch master data, debounce pencarian, skeleton loading, cache TanStack Query |

---

## Lampiran A — Daftar Fitur Desktop → Web (Checklist Paritas)

| Modul | Fitur | Web |
|---|---|---|
| Sidebar | 8 menu navigasi, brand, logout | ✅ |
| Dashboard | 4 KPI, filter hari/minggu/bulan/custom, catatan kaki | ✅ |
| Harian | 4 tab + search debounce + edit mode + soft delete + cascade | ✅ |
| Harian | Dropdown sumber kain (MODAL OPEN), sisa qty distribusi, auto-kode batch | ✅ |
| Harian | Sinkron otomatis ClientReceivable dari penjualan offline | ✅ |
| Hutang | Multi-select, batch payment FIFO, batal lunas, kode batch auto `PRD-MMYY-XXX`, PDF nota | ✅ |
| Gaji | 4 tab; dedup SalaryRun; update BonBalance & BonMovement; PDF slip; import/export Excel; absensi + tarif normal/lembur | ✅ |
| Stok | Staging BigSeller; export IN/OUT xlsx | ✅ |
| Invoice | Tabel gabungan FIFO; deposit/diskon/jatuh tempo/metode; PDF invoice; hapus pembayaran; self-healing receivable | ✅ |
| Profit | Analisis batch; konstanta biaya; toggle FULL CUT; simpan profit_history; warning SKU tanpa harga | ✅ |
| Master | SKU, Person, Klien; proteksi hapus FK; import Excel + log error | ✅ |
| Payroll | Replikasi startup-sync `TarifMaster → MasterTarifPenjahit` | ✅ (catatan) |
| Auth | Login single admin, JWT cookie, rate-limit, logout | ✅ (baru) |

---

*Dokumen ini adalah rancangan konsep. Setelah disetujui, implementasi dimulai dari Fase 0.*
