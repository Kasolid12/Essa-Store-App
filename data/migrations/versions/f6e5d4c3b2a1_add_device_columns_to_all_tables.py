"""add created_by_device / updated_by_device to all tables (kepemilikan baris)

Revision ID: f6e5d4c3b2a1
Revises: a1b2c3d4e5f6
Create Date: 2026-08-07 00:00:00.000000

Tujuan (Fase 6.3 — CLOUD_DATABASE_GUIDE.md):
  Kolom `created_by_device` / `updated_by_device` memberi kepemilikan baris yang
  PASTI antar perangkat — menggantikan heuristik backfill (perbandingan isi)
  saat perangkat standalone bergabung ke cloud:
    - created_by_device : diisi saat INSERT oleh aplikasi (event di base.py)
                           dengan device_id perangkat pembuat.
    - updated_by_device : diisi setiap UPDATE oleh perangkat yang mengedit.
  Sinkronisasi dua arah (utils/cloud_sync.py) memakai created_by_device untuk
  memutuskan "baris yang sama vs tabrakan id" tanpa menebak-nebak dari isi.

Catatan:
  - Kolom dibuat NULLABLE tanpa default -> aman, tidak butuh backfill.
    NULL = baris lama (dibuat sebelum Fase 6.3) — sync tetap memakai heuristik
    lama hanya untuk baris yang kepemilikannya belum diketahui (NULL).
  - Batch mode dipakai agar aman di SQLite (native ADD COLUMN) maupun Postgres.
  - Diterapkan ke CLOUD (Neon):  CLOUD_DATABASE_URL=... alembic upgrade head
    Diterapkan ke LOKAL (essa.db): CLOUD_DATABASE_URL= alembic upgrade head
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6e5d4c3b2a1'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = [
    "sku_master",
    "persons",
    "clients",
    "garapan_rates",
    "tarif_master",
    "master_tarif_penjahit",
    "app_settings",
    "debt_entries",
    "debt_payments",
    "hasil_cutting",
    "distribusi_cutting",
    "modal_operasional",
    "pengeluaran_offline",
    "bon_balances",
    "bon_movements",
    "salary_runs",
    "salary_line_items",
    "pengsup_reconciliation",
    "attendance_records",
    "invoices",
    "invoice_lines",
    "client_receivables",
    "client_receivable_payments",
    "stock_movements",
    "audit_log",
    "profit_history",
]


def upgrade() -> None:
    """Upgrade schema."""
    for t in _TABLES:
        with op.batch_alter_table(t) as batch_op:
            batch_op.add_column(
                sa.Column("created_by_device", sa.String(), nullable=True)
            )
            batch_op.add_column(
                sa.Column("updated_by_device", sa.String(), nullable=True)
            )


def downgrade() -> None:
    """Downgrade schema."""
    for t in _TABLES:
        with op.batch_alter_table(t) as batch_op:
            batch_op.drop_column("updated_by_device")
            batch_op.drop_column("created_by_device")
