"""add profit_history table

Revision ID: b7e1a2c3d4f5
Revises: c9b50081130a
Create Date: 2026-06-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e1a2c3d4f5'
down_revision: Union[str, Sequence[str], None] = 'c9b50081130a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'profit_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tanggal_hitung', sa.String(), nullable=False),
        sa.Column('debt_entry_id', sa.Integer(), nullable=True),
        sa.Column('total_pendapatan', sa.Float(), nullable=False),
        sa.Column('total_modal_kain', sa.Float(), nullable=False),
        sa.Column('total_modal_jahit', sa.Float(), nullable=False),
        sa.Column('total_profit', sa.Float(), nullable=False),
        sa.Column('periode_mulai', sa.String(), nullable=False),
        sa.Column('periode_akhir', sa.String(), nullable=False),
        sa.Column('catatan', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['debt_entry_id'], ['debt_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_profit_history_tanggal_hitung'), 'profit_history', ['tanggal_hitung'], unique=False)
    op.create_index(op.f('ix_profit_history_debt_entry_id'), 'profit_history', ['debt_entry_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_profit_history_debt_entry_id'), table_name='profit_history')
    op.drop_index(op.f('ix_profit_history_tanggal_hitung'), table_name='profit_history')
    op.drop_table('profit_history')
