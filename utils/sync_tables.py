"""Daftar tabel yang disinkronkan + urutan pemrosesan bersama.

Dipakai oleh:
  - scripts/seed_cloud.py   (seed awal: SQLite -> cloud)
  - utils/cloud_sync.py     (sinkronisasi berkala: SQLite -> cloud)

Urutan INSERT: tabel induk (parent) dulu, lalu tabel anak — agar foreign key
terpenuhi. Urutan DELETE: kebalikannya (anak dulu).
Tabel dengan self-FK (sku_master) diurutkan by id saat diambil.
"""
TABLE_ORDER = [
    "sku_master",               # self-FK parent_sku_id → diurutkan by id
    "persons",
    "clients",
    "garapan_rates",
    "tarif_master",
    "master_tarif_penjahit",
    "app_settings",
    "debt_entries",
    "debt_payments",
    "hasil_cutting",            # FK → debt_entries (modal_hutang_id)
    "distribusi_cutting",       # FK → hasil_cutting
    "modal_operasional",
    "pengeluaran_offline",      # FK → clients, persons, sku_master
    "bon_balances",
    "bon_movements",
    "salary_runs",
    "salary_line_items",        # FK → master_tarif_penjahit (tarif_id)
    "pengsup_reconciliation",
    "attendance_records",
    "invoices",
    "invoice_lines",
    "client_receivables",       # FK → invoices, clients, persons
    "client_receivable_payments",
    "payment_allocations",      # FK → client_receivable_payments, pengeluaran_offline
    "stock_movements",
    "audit_log",
    "profit_history",           # FK → debt_entries
]
