"""make client_receivables.person_id nullable

Revision ID: e4fc4d7866da
Revises: d8e3f4a5b6c7
Create Date: 2026-07-21 18:30:36.557837

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4fc4d7866da'
down_revision: Union[str, Sequence[str], None] = 'd8e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite does not support ALTER COLUMN, so we use batch_alter_table
    # which recreates the table with the new schema
    
    # Make client_receivables.person_id nullable (ini adalah fix utama)
    with op.batch_alter_table('client_receivables') as batch_op:
        batch_op.alter_column('person_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    # Change pengeluaran_offline.qty from INTEGER to Float
    with op.batch_alter_table('pengeluaran_offline') as batch_op:
        batch_op.alter_column('qty',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('pengeluaran_offline') as batch_op:
        batch_op.alter_column('qty',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=False)

    with op.batch_alter_table('client_receivables') as batch_op:
        batch_op.alter_column('person_id',
               existing_type=sa.INTEGER(),
               nullable=False)
