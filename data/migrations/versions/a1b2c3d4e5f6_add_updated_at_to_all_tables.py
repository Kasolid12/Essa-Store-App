"""add updated_at to all tables (fondasi sinkronisasi dua arah)

Revision ID: a1b2c3d4e5f6
Revises: e4fc4d7866da
Create Date: 2026-08-06 00:00:00.000000

Tujuan (Fase 5.5 — fondasi Fase 6 di CLOUD_DATABASE_GUIDE.md):
  Kolom `updated_at` adalah dasar deteksi konflik *last-write-wins* untuk
  sinkronisasi dua arah penuh antar perangkat. Tabel berikut BELUM punya
  `updated_at` (21 tabel):

    garapan_rates, tarif_master, master_tarif_penjahit, hasil_cutting,
    distribusi_cutting, modal_operasional, pengeluaran_offline, debt_entries,
    debt_payments, bon_movements, salary_runs, salary_line_items,
    pengsup_reconciliation, attendance_records, invoices, invoice_lines,
    client_receivables, client_receivable_payments, stock_movements,
    profit_history, audit_log

  Tabel yang SUDAH punya `updated_at` TIDAK disentuh:
    persons, clients, bon_balances, app_settings, sku_master

Catatan:
  - Kolom dibuat NULLABLE tanpa default -> aman, tidak butuh backfill.
  - Aplikasi akan mulai mengisi kolom ini pada Fase 6 (perubahan model +
    jalur tulis). Sampai saat itu kolom hanya placeholder dan tidak ikut
    disinkronkan (sync memfilter kolom yang tidak ada di DB lokal).
  - Batch mode dipakai agar aman di SQLite (native ADD COLUMN) maupun Postgres.
  - PENTING: migration ini dirancang untuk CLOUD (Neon). Bila `alembic upgrade
    head` dijalankan TANPA memuat .env (CLOUD_DATABASE_URL kosong), alembic akan
    menerapkannya ke DB LOKAL (essa.db) — menambah kolom nullable yang belum
    dipakai aplikasi. Aman, tapi sadarilah itu mengubah file DB lokal Anda.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e4fc4d7866da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = [
    "garapan_rates", "tarif_master", "master_tarif_penjahit", "hasil_cutting",
    "distribusi_cutting", "modal_operasional", "pengeluaran_offline",
    "debt_entries", "debt_payments", "bon_movements", "salary_runs",
    "salary_line_items", "pengsup_reconciliation", "attendance_records",
    "invoices", "invoice_lines", "client_receivables",
    "client_receivable_payments", "stock_movements", "profit_history",
    "audit_log",
]


def upgrade() -> None:
    """Upgrade schema."""
    for t in _TABLES:
        with op.batch_alter_table(t) as batch_op:
            batch_op.add_column(
                sa.Column("updated_at", sa.DateTime(), nullable=True)
            )


def downgrade() -> None:
    """Downgrade schema."""
    for t in _TABLES:
        with op.batch_alter_table(t) as batch_op:
            batch_op.drop_column("updated_at")
