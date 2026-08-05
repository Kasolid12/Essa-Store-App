"""Fase 3 — Buat skema database cloud (Neon PostgreSQL) langsung dari model.

Alasan memakai create_all (bukan `alembic upgrade head`):
  Skema DB live (`essa.db`) dibangun dari model yang sudah berevolusi dan memiliki
  kolom yang TIDAK ada di migration Alembic (lihat CLOUD_DATABASE_GUIDE.md §Fase 3).
  Membuat skema dari model menjamin cloud identik dengan ekspektasi aplikasi.
  Setelah skema jadi, jalankan:  alembic stamp head

Cara pakai (bash Windows):
    set -a; source .env; set +a
    python scripts/create_cloud_schema.py

Wajib: CLOUD_DATABASE_URL terisi di file .env
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect

from data.database import get_cloud_engine
from data.models.base import Base
import data.models  # noqa: F401 — daftarkan semua model ke Base.metadata


def main() -> None:
    engine = get_cloud_engine()
    if engine is None:
        print("ERROR: CLOUD_DATABASE_URL belum diatur di file .env")
        sys.exit(1)

    print("Membuat skema di cloud (PostgreSQL/Neon) ...")
    Base.metadata.create_all(bind=engine)

    tables = sorted(inspect(engine).get_table_names())
    print(f"Selesai. {len(tables)} tabel berhasil dibuat di cloud:")
    for t in tables:
        print(f"  - {t}")


if __name__ == "__main__":
    main()
