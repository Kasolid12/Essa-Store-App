# app_essa/data/models/base.py (or data/models/base.py depending on your exact folder name)

from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    This is the foundational class that all other SQLAlchemy models inherit from.
    Alembic uses this Base to find all your tables and generate the migrations.
    """
    pass


# ---------------------------------------------------------------------
# Kepemilikan baris antar perangkat (Fase 6.3)
# ---------------------------------------------------------------------
# ID perangkat yang sedang dipakai, diisi saat aplikasi start (main.py) dan
# saat sinkronisasi (utils/cloud_sync.py). Dipakai event di bawah ini untuk
# mengisi kolom created_by_device / updated_by_device pada SEMUA model secara
# otomatis - tidak perlu menyentuh tiap jalur tulis di views.
#
#   - created_by_device : diisi HANYA saat INSERT (identitas pembuat baris).
#   - updated_by_device : diisi setiap UPDATE (perangkat yang terakhir edit).
#
# NULL = baris lama (dibuat sebelum Fase 6.3). Sync memakai created_by_device
# untuk memutuskan "baris yang sama vs tabrakan" secara PASTI antar perangkat.
CURRENT_DEVICE_ID = None


def _fill_device_creator(mapper, connection, target):
    """Isi created_by_device saat INSERT (bila kolomnya ada & masih kosong)."""
    if CURRENT_DEVICE_ID is None:
        return
    if "created_by_device" in target.__table__.columns \
            and getattr(target, "created_by_device", None) is None:
        target.created_by_device = CURRENT_DEVICE_ID


def _mark_device_editor(mapper, connection, target):
    """Isi updated_by_device setiap UPDATE (perangkat yang terakhir mengedit)."""
    if CURRENT_DEVICE_ID is None:
        return
    if "updated_by_device" in target.__table__.columns:
        target.updated_by_device = CURRENT_DEVICE_ID


# propagate=True: berlaku untuk SEMUA subclass (mapper turunan), bukan hanya Base.
event.listen(Base, "before_insert", _fill_device_creator, propagate=True)
event.listen(Base, "before_update", _mark_device_editor, propagate=True)
