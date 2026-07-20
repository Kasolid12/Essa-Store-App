"""add clients table and client_id references

Revision ID: d8e3f4a5b6c7
Revises: b7e1a2c3d4f5
Create Date: 2026-07-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'd8e3f4a5b6c7'
down_revision: Union[str, Sequence[str], None] = 'b7e1a2c3d4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- 1. Create clients table ---
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nama', sa.String(), nullable=False),
        sa.Column('alamat', sa.String(), nullable=True),
        sa.Column('no_hp', sa.String(), nullable=True),
        sa.Column('catatan', sa.String(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('is_deleted', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clients_nama'), 'clients', ['nama'], unique=False)

    # --- 2. Add client_id to pengeluaran_offline ---
    op.add_column('pengeluaran_offline', sa.Column('client_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_pengeluaran_offline_client_id'), 'pengeluaran_offline', ['client_id'], unique=False)
    op.create_foreign_key('fk_pengeluaran_offline_client_id', 'pengeluaran_offline', 'clients', ['client_id'], ['id'])

    # --- 3. Add client_id to client_receivables ---
    op.add_column('client_receivables', sa.Column('client_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_client_receivables_client_id'), 'client_receivables', ['client_id'], unique=False)
    op.create_foreign_key('fk_client_receivables_client_id', 'client_receivables', 'clients', ['client_id'], ['id'])

    # Make person_id nullable in client_receivables (it was previously NOT NULL)
    # SQLite doesn't support ALTER COLUMN, so we handle this with batch mode
    # But for simplicity, we just leave person_id as nullable already works in sqlalchemy

    # --- 4. Migrate data: Person (type='KLIEN') → Client ---
    connection = op.get_bind()
    
    # Get all persons with person_type='KLIEN'
    persons = connection.execute(
        text("SELECT id, nama, no_hp, alamat, catatan FROM persons WHERE person_type = 'KLIEN' AND is_deleted = 0")
    ).fetchall()
    
    for p in persons:
        # Insert into clients
        result = connection.execute(
            text("""
                INSERT INTO clients (nama, alamat, no_hp, catatan, is_active, is_deleted, created_at, updated_at)
                VALUES (:nama, :alamat, :no_hp, :catatan, 1, 0, datetime('now'), datetime('now'))
            """),
            {"nama": p.nama, "alamat": p.alamat, "no_hp": p.no_hp, "catatan": p.catatan}
        )
        # Get the new client id
        client_id = connection.execute(text("SELECT last_insert_rowid()")).scalar()
        
        # Update pengeluaran_offline references
        connection.execute(
            text("UPDATE pengeluaran_offline SET client_id = :client_id WHERE person_id = :person_id"),
            {"client_id": client_id, "person_id": p.id}
        )
        
        # Update client_receivables references
        connection.execute(
            text("UPDATE client_receivables SET client_id = :client_id WHERE person_id = :person_id"),
            {"client_id": client_id, "person_id": p.id}
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign keys first
    op.drop_constraint('fk_pengeluaran_offline_client_id', 'pengeluaran_offline', type_='foreignkey')
    op.drop_constraint('fk_client_receivables_client_id', 'client_receivables', type_='foreignkey')
    
    # Remove indexes
    op.drop_index(op.f('ix_pengeluaran_offline_client_id'), table_name='pengeluaran_offline')
    op.drop_index(op.f('ix_client_receivables_client_id'), table_name='client_receivables')
    op.drop_index(op.f('ix_clients_nama'), table_name='clients')
    
    # Remove columns
    op.drop_column('pengeluaran_offline', 'client_id')
    op.drop_column('client_receivables', 'client_id')
    
    # Drop table
    op.drop_table('clients')
