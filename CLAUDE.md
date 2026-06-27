# CLAUDE.md

Project memory for AI assistants working on Essa-Store-App. Keep this file lean — only facts that future sessions need to NOT re-derive from code/git.

---

## 1. Project Overview

**Essa Store App** — desktop operational app for a convection (garment) business.

- **Domain**: daily + weekly operations of a konveksi (tailoring shop):
  hutang kain → cutting → distribusi ke penjahit/sub → gaji & bon → invoice/piutang → profit.
- **UI lang**: Indonesian.
- **Entry point**: `main.py`.

---

## 2. Stack

| Layer | Tech |
|-------|------|
| Language | Python 3.14 (CPython) |
| DB | SQLite (`essa.db`) via **SQLAlchemy** + **Alembic** (migrations) |
| GUI | **PySide6 / Qt** — custom widgets (`ui/theme.py`, `ui/components/`). **NOT Tkinter.** |
| PDF | `utils/pdf_engine.py` |
| Backup | `utils/backup_engine.py` |

Navigation pattern: `CyberButton` sidebar + `QStackedWidget`. Views are lazy-loaded via `switch_page` (`main.py`); Dashboard is the only view pre-loaded in `build_content_area`.

---

## 3. Folder Layout

```
root/
├── main.py                    # Entry point — registers all views/menus
├── essa.db                    # Main SQLite database (DO NOT touch directly)
├── data/
│   ├── database.py            # Session factory, engine
│   ├── dashboard_queries.py   # Aggregations used by dashboard_view
│   ├── models/
│   │   ├── base.py
│   │   ├── bon.py             # bon_balances, bon_movements
│   │   ├── catatan_harian.py  # hasil_cutting, distribusi_cutting,
│   │   │                       #   pengeluaran_offline, modal_operasional
│   │   ├── debt.py            # debt_entries, debt_payments
│   │   ├── invoice.py         # invoices, invoice_lines,
│   │   │                       #   client_receivables, client_receivable_payments
│   │   ├── master.py          # app_settings, tarif_master,
│   │   │                       #   garapan_rates, master_tarif_penjahit
│   │   ├── person.py          # persons
│   │   ├── profit_history.py  # ProfitHistory (added session 3)
│   │   ├── salary.py          # salary_runs, salary_line_items,
│   │   │                       #   attendance_records, pengsup_reconciliation
│   │   ├── sku.py             # sku_master
│   │   └── stock_audit.py     # stock_movements
│   └── migrations/
├── ui/
│   ├── theme.py
│   ├── components/
│   │   ├── buttons.py
│   │   └── tables.py
│   └── views/                 # One file per sidebar menu
└── utils/
    ├── pdf_engine.py
    └── backup_engine.py
```

---

## 4. Database Schema

Verified from `essa.db`. **Do NOT re-inspect** — this section is the source of truth.

### 4.1 Payroll (`salary_runs` family — DO NOT recreate)
- **`salary_runs`**: `id`, `tipe` (penjahit/sub/karyawan), `person_id`,
  `periode_mulai`, `periode_akhir`, `tanggal_proses`,
  `gaji_kotor`, `bon_lama`, `tambah_bon`, `potong_bon`, `gaji_bersih`, `sisa_bon_akhir`,
  `pdf_path`, `excel_path`, `catatan`, `is_deleted`, `created_at`.
- **`salary_line_items`**: `salary_run_id`, `sku_id`, `tarif_id`, `model_code`,
  `qty`, `tarif_per_pcs`, `subtotal`.
- **`attendance_records`**: `salary_run_id`, `person_id`, `tanggal`, `tap_masuk`,
  `tap_keluar`, `total_menit`, `menit_normal`, `menit_lembur`, `tarif_normal`,
  `tarif_lembur`, `pendapatan`.
- **`pengsup_reconciliation`**: `salary_run_id`, `tipe`, `sku_id`, `qty`,
  `harga_per_unit`, `subtotal`.

### 4.2 Debt & Receivables
- **`debt_entries`** (hutang kain & barang): `id`, `tipe_hutang`, `tanggal`,
  `kode_produksi`, `status_cutting`, `person_id`, `keterangan`, `sku_id`, `qty`,
  `nominal_hutang`, `status`, `is_deleted`.
- **`debt_payments`**: `id`, `debt_entry_id`, `tanggal_bayar`, `nominal_bayar`,
  `metode`, `bon_used`, `is_deleted`.
- **`client_receivables`** (piutang): `id`, `invoice_id` (nullable), `person_id`,
  `nominal`, `sisa`, `status`.
- **`client_receivable_payments`**: `id`, `receivable_id`, `tanggal_bayar`,
  `nominal_bayar`, `metode`.

### 4.3 Cutting & Operational
- **`hasil_cutting`**: `id`, `tanggal`, `kode_produksi`, `sku_id`, `qty`,
  `modal_hutang_id` (FK→`debt_entries.id`), `is_deleted`.
- **`distribusi_cutting`**: `id`, `tanggal`, `kode_produksi`, `person_id`,
  `jenis`, `sku_id`, `qty`, `hasil_cutting_id` (FK→`hasil_cutting.id`), `is_deleted`.
- **`pengeluaran_offline`**: `id`, `tanggal`, `sku_id`, `qty`, `harga_satuan`,
  `total`, `person_id`, `is_deleted`.
- **`modal_operasional`**: `id`, `tanggal`, `jenis`, `keterangan`, `nominal`,
  `is_deleted`. Field `jenis` is an enum; the `overhead` value has been removed
  from the UI (frontend no longer shows it).

### 4.4 Profit History (added session 3)
- **`profit_history`**: `id`, `tanggal_hitung` (VARCHAR), `debt_entry_id`
  (INT nullable, FK→`debt_entries.id`), `total_pendapatan`, `total_modal_kain`,
  `total_modal_jahit`, `total_profit` (FLOAT),
  `periode_mulai`, `periode_akhir` (VARCHAR), `catatan` (VARCHAR nullable),
  `created_at` (DATETIME).
- Migration id: `b7e1a2c3d4f5` (applied).
- Written by `ProfitSimulationView.save_profit_history()` via upsert keyed on
  `debt_entry_id` (one row per batch).

### 4.5 Master & Misc
- **`sku_master`**: `id`, `kode_sku`, `nama_produk`, `parent_sku_id`, `kategori`,
  `model`, `warna`, `ukuran`, `harga_jual`, `harga_modal`, `kain_cost`,
  `potongan_cost`, `is_active`, `is_deleted`.
- **`persons`**: `id`, `nama`, `person_type`
  (karyawan/penjahit/sub/klien/supplier), `no_hp`, `alamat`, `is_active`, `is_deleted`.
- **`stock_movements`**: `id`, `tanggal`, `sku_id`, `tipe`, `qty`, `sumber_ref`,
  `catatan`.
- Also present but rarely touched: `bon_balances`, `bon_movements`, `invoices`,
  `invoice_lines`, `audit_log`, `app_settings`.

---

## 5. Critical Relations

- `hasil_cutting.modal_hutang_id` → `debt_entries.id`
- `distribusi_cutting.hasil_cutting_id` → `hasil_cutting.id`
- `salary_runs.person_id` → `persons.id`
- `client_receivables.invoice_id` → `invoices.id` (nullable)
- `profit_history.debt_entry_id` → `debt_entries.id` (nullable)

---

## 6. Reference Queries (used by dashboard)

These are the canonical aggregations. Reuse from `data/dashboard_queries.py` —
do not rewrite inline in views.

### 6.1 Total Hutang Tersisa
```sql
SELECT SUM(de.nominal_hutang) - COALESCE(SUM(dp.nominal_bayar), 0)
FROM debt_entries de
LEFT JOIN debt_payments dp ON dp.debt_entry_id = de.id AND dp.is_deleted = 0
WHERE de.is_deleted = 0 AND de.status != 'lunas'
```

### 6.2 Total Piutang
```sql
SELECT SUM(sisa) FROM client_receivables WHERE status != 'lunas'
```

### 6.3 Akumulasi Gaji Karyawan (overhead — penjahit/sub excluded)
```sql
SELECT SUM(gaji_bersih) FROM salary_runs
WHERE tipe = 'karyawan' AND is_deleted = 0
AND tanggal_proses BETWEEN :mulai AND :akhir
```

### 6.4 Profit Produksi (period-bounded)
```sql
SELECT SUM(total_profit) FROM profit_history
WHERE tanggal_hitung BETWEEN :mulai AND :akhir
```

---

## 7. Menus (current state)

| Menu | View File | Status |
|------|-----------|--------|
| Dashboard | `dashboard_view.py` | ✅ Done (session 4) |
| Catatan Harian | `harian_view.py` | ✅ Stable |
| Hutang Pelunasan | `hutang_view.py` | ✅ Stable |
| Payroll & Bon | `gaji_view.py` | ✅ Stable; data lives in `salary_runs` |
| Manajemen Stock | `stock_view.py` | ✅ Stable (Live Dashboard tab removed) |
| Invoice Piutang | `invoice_view.py` | ✅ Stable |
| Profit Simulation | `profit_view.py` | ✅ Saves to `profit_history` |
| Data Manager | `master_view.py` | ✅ Stable |
| ~~BI Agent~~ | — | ❌ Removed (do not re-add) |

All previously open bugs in `catatan_harian ↔ hutang ↔ profit` were resolved in session 5.

---

## 8. Active Work — Session 8 (2026-06-27)

### Task A: Excel Importer (`data/excel_importer.py`)
- **`import_sku_from_excel(filepath, session)`**: Baca MasterSKU.xlsx → upsert ke `SkuMaster`.
  Format sheet "Master SKU": [Nomor SKU, Judul, Rata-Rata Modal Bobot].
- **`import_tarif_from_excel(filepath, session)`**: Baca Master_tarif.xlsx → upsert ke `TarifMaster`.
  Sheet "SKU_Pengsup": [Nomor SKU, Kain, Potongan] → `tarif_pengsup_kain`, `tarif_pengsup_potongan`.
  Sheet "SKU_Penjahit": [SKU, Harga Satuan] → `tarif_jahit`.
- **UI**: Tab baru "IMPORT EXCEL" di `master_view.py` — tombol pilih file + import.

### Task B: Dashboard Profit Full-Cut Filter
- **`data/dashboard_queries.py`** → `get_profit_produksi()`:
  LEFT JOIN `profit_history` ↔ `debt_entries` via `debt_entry_id`.
  Hanya hitung profit jika `de.status_cutting = 'SELESAI'` (full cut) atau `ph.debt_entry_id IS NULL`.
  Status full-cut di-toggle via tombol "TANDAI KAIN HABIS (FULL CUT)" di Profit Simulation.

### Task C: Bug Fix Payroll — "int object has no attribute is_integer"
- ✅ Root cause: `SalaryLineItem.qty` adalah Integer column → `item.qty` return `int`, tapi dipanggil `.is_integer()` method milik `float`.
- ✅ Fix: 4 baris di `utils/pdf_engine.py` — wrapping `float(item.qty)` sebelum `.is_integer()`.
- ✅ Semua tab payroll dicek: Penjahit ✅, Pengsup ✅, Karyawan ✅, Bon ✅.

### Task D: Fix Edit Jam Absensi Karyawan (read-only table)
- ✅ Root cause: `CyberTable` default `NoEditTriggers` — tabel edit absensi tidak bisa diedit.
- ✅ Fix: Override `setEditTriggers(DoubleClicked)` di `setup_tab_edit_karyawan()`.
- ✅ Alur: double-click jam masuk/keluar → isi format `HH:MM` → tombol "HITUNG ULANG & TERAPKAN".

### Task E: Karyawan diedit hilang dari PDF (format mismatch)
- ✅ Root cause: `submit_edit_karyawan()` simpan tarif dgn "Rp" (`"Rp 150"`) tapi `submit_pasukan()` parsing tanpa hapus "Rp" → ValueError → skip karyawan.
- ✅ Fix: simpan tarif tanpa "Rp" (`f"{tarif_normal:g}"`) + `.replace('Rp ','')` di parsing submit_pasukan.
- ✅ Defense-in-depth untuk data lama.

### Task F: Column misalignment di tabel default Gaji Karyawan
- ✅ Root cause: `load_karyawan_data()` pakai col index 5-8, tapi seharusnya 7-10 (tambah 2 kolom baru: Menit Lembur & Tarif Lembur di posisi 5-6).
- ✅ Fix: Col 5-6 diisi "0" (dulu tidak diisi); Col 7 ← Gaji Kotor; Col 8 ← Bon Lama; Col 9 ← Potong Kasbon; Col 10 ← Gaji Bersih.
- ✅ Verifikasi semua fungsi rujuk col index yang sama (`submit_pasukan`, `submit_edit_karyawan`, `import_absensi_excel`, `recalc_pasukan`, `buka_editor_karyawan`).

### Status Rules
- ✅ Selesai
- ❌ Belum dikerjakan

---

## 9. Session Log (frozen — for context only)

Setiap entry = satu session kerja. Format: satu baris per session.
Lihat Rule 10.9 untuk panduan penulisan.

1. ✅ Session 1–2: Removed bi_agent/Live Dashboard/overhead; built dashboard query functions.
2. ✅ Session 3: Added profit_history model + migration + wired up profit_view.py.
3. ✅ Session 4: Built dashboard_view.py (layout + data wiring) + registered in main.py.
4. ✅ Session 5 (2026-06-24): Bug-fixed catatan_harian↔hutang↔profit flow; fixed StockView helper.
5. ✅ Session 6 (2026-06-25): Fitur Search Global & Tombol Hapus di Catatan Harian.
6. ✅ Session 7 (2026-06-26): Font PDF Courier→Helvetica; Profit tanggal kain acuan dari Hutang; Anti-duplicate payroll; Auto-sinkron Data Manager→semua menu; Fix edit/hapus Pengeluaran Offline.
7. ✅ Session 8 (2026-06-27): Excel Importer (import SKU + Tarif dari Excel); Dashboard Profit hanya tampilkan batch Full Cut.

No historical "TODO" / "ada bug" lines should remain in code unless explicitly
re-opened by the user.

---

## 10. Hard Rules (anti-thrashing)

Before touching anything, re-read this list.

1. ❌ **Do not** open, read, or query `essa.db` directly. Schema is documented above.
2. ❌ **Do not** load more than ~3 Python files per turn — read the project structure
   incrementally.
3. ❌ **Do not** run Alembic migrations without explicit user confirmation.
4. ✅ If real data is needed, **ask the user to query it** and paste the result.
5. ❌ **Do not** touch `backups/` or `exports/` — managed by `utils/backup_engine.py`.
6. ✅ Match existing code style: comment density, naming, idioms of the file you're editing.
7. ✅ Before deleting or overwriting, re-read the target — surface contradictions
   instead of silently proceeding.
8. ✅ Confirm before any hard-to-reverse or outward-facing action.
9. ✅ **Session Log satu baris per session.** Setiap entry di Session Log (section 9)
   hanya satu baris, format: `N. ✅ Session X (YYYY-MM-DD): Deskripsi singkat —
   file terkunci.` Tidak perlu detail teknis panjang; simpan di Active Work saja.
