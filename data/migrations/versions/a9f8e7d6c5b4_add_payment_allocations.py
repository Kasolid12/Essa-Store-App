"""add payment_allocations (alokasi pembayaran ke transaksi penjualan)

Revision ID: a9f8e7d6c5b4
Revises: f6e5d4c3b2a1
Create Date: 2026-09-17 00:00:00.000000

Tujuan:
  Menyimpan pemetaan "pembayaran X melunasi Rp N dari penjualan Y" agar status
  LUNAS/PARTIAL/BELUM LUNAS per transaksi di menu Invoice & Piutang mengikuti
  pilihan user saat pelunasan — bukan sekadar asumsi FIFO berdasarkan tanggal.

Catatan:
  - Pembayaran lama (sebelum revisi ini) tidak punya baris alokasi; UI
    memfallback-nya ke FIFO terhadap transaksi terlama (perilaku lama).
  - Diterapkan ke LOKAL (essa.db):  alembic upgrade head
    Diterapkan ke CLOUD (Neon):     CLOUD_DATABASE_URL=... alembic upgrade head
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f8e7d6c5b4'
down_revision: Union[str, Sequence[str], None] = 'f6e5d4c3b2a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'payment_allocations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('sales_id', sa.Integer(), nullable=False),
        sa.Column('nominal', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_device', sa.String(), nullable=True),
        sa.Column('updated_by_device', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['payment_id'], ['client_receivable_payments.id']),
        sa.ForeignKeyConstraint(['sales_id'], ['pengeluaran_offline.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_payment_allocations_payment_id', 'payment_allocations', ['payment_id']
    )
    op.create_index(
        'ix_payment_allocations_sales_id', 'payment_allocations', ['sales_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_payment_allocations_sales_id', table_name='payment_allocations')
    op.drop_index('ix_payment_allocations_payment_id', table_name='payment_allocations')
    op.drop_table('payment_allocations')
