"""Fase 4 — Seed data awal: SQLite lokal (essa.db) → cloud (Neon PostgreSQL).

Menyalin seluruh data dari database lokal ke database cloud dengan
MEM-PERTAHANKAN ID asli, sehingga relasi foreign key antar baris tetap valid.

SANITASI FK: SQLite tidak menegakkan foreign key, sehingga data lama bisa berisi
nilai FK yang menunjuk id yang tidak ada (contoh: parent_sku_id = 0 untuk "tanpa
induk"). PostgreSQL menegakkan FK, maka nilai FK yang menunjuk id tidak ada
dinormalisasi menjadi NULL (perilaku aplikasi tetap sama).

KOLOM GENERATED: kolom computed (mis. persons.nama_uppercase) tidak ikut di-insert
— di Postgres kolom generated diisi otomatis oleh server.

Cara pakai (bash Windows, dari root proyek):
    python scripts/seed_cloud.py

Wajib:
  - CLOUD_DATABASE_URL terisi di .env
  - Skema cloud sudah dibuat (jalankan dulu scripts/create_cloud_schema.py)
  - Cloud masih kosong (seed hanya boleh dijalankan sekali)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect as sa_inspect, table as sa_table, column as sa_column, text

from data.database import engine as local_engine, get_cloud_engine
from utils.sync_tables import TABLE_ORDER


def _sanitize_rows(tname, rows, fk_col_to_ref, id_sets, batch_id_set):
    """Normalisasi nilai FK yang menunjuk id yang tidak ada menjadi NULL."""
    cleaned = []
    for r in rows:
        d = dict(r)
        for fk_col, ref_table in fk_col_to_ref.items():
            val = d.get(fk_col)
            if val is None:
                continue
            ref_ids = batch_id_set if ref_table == tname else id_sets.get(ref_table)
            if ref_ids is not None and val not in ref_ids:
                d[fk_col] = None
        cleaned.append(d)
    return cleaned


def main() -> None:
    cloud_engine = get_cloud_engine()
    if cloud_engine is None:
        print("ERROR: CLOUD_DATABASE_URL belum diatur di file .env")
        sys.exit(1)

    local_insp = sa_inspect(local_engine)
    cloud_insp = sa_inspect(cloud_engine)

    local_tables = set(local_insp.get_table_names())
    cloud_tables = set(cloud_insp.get_table_names())

    missing = [t for t in TABLE_ORDER if t not in cloud_tables]
    if missing:
        print(f"ERROR: tabel berikut belum ada di cloud: {missing}")
        print("Jalankan dulu: python scripts/create_cloud_schema.py")
        sys.exit(1)

    # Cegah seed ganda — cloud harus kosong.
    with cloud_engine.connect() as cc:
        for probe in ("clients", "sku_master", "persons"):
            if probe in cloud_tables:
                n = cc.execute(text(f"SELECT COUNT(*) FROM {probe}")).scalar()
                if n > 0:
                    print(f"ERROR: cloud sudah berisi data (tabel {probe} = {n} baris).")
                    print("Seed hanya boleh dijalankan sekali pada cloud kosong.")
                    sys.exit(1)

    stats = []
    id_sets = {}  # tabel -> set id yang sudah di-insert ke cloud
    print("Menyalin data lokal -> cloud ...")
    with local_engine.connect() as lc, cloud_engine.begin() as cc:
        for tname in TABLE_ORDER:
            if tname not in local_tables:
                continue
            # Kolom INSERT ditentukan oleh SKEMA CLOUD, tanpa kolom generated/computed
            # (mis. persons.nama_uppercase) — di Postgres kolom generated diisi otomatis.
            cloud_cols = [
                c["name"] for c in cloud_insp.get_columns(tname) if not c.get("computed")
            ]
            local_cols = {c["name"] for c in local_insp.get_columns(tname)}
            missing_local = [c for c in cloud_cols if c not in local_cols]
            if missing_local:
                print(f"ERROR: kolom {missing_local} pada {tname} tidak ada di DB lokal.")
                sys.exit(1)

            sel = ", ".join(f'"{c}"' for c in cloud_cols)
            order_by = ' ORDER BY "id"' if "parent_sku_id" in cloud_cols else ""
            rows = lc.execute(text(f'SELECT {sel} FROM "{tname}"{order_by}')).mappings().all()
            if not rows:
                stats.append((tname, 0))
                print(f"  - {tname}: 0 baris (kosong)")
                continue

            # Peta kolom FK -> tabel referensi (dari skema cloud)
            fk_col_to_ref = {}
            for fk in cloud_insp.get_foreign_keys(tname):
                if len(fk["constrained_columns"]) == 1:
                    fk_col_to_ref[fk["constrained_columns"][0]] = fk["referred_table"]
                else:
                    print(f"  [PERINGATAN] FK multi-kolom di {tname} dilewati sanitasi")

            batch_id_set = set(r["id"] for r in rows) if "id" in cloud_cols else None
            cleaned = _sanitize_rows(tname, rows, fk_col_to_ref, id_sets, batch_id_set)

            t = sa_table(tname, *[sa_column(c) for c in cloud_cols])
            cc.execute(t.insert(), cleaned)
            id_sets[tname] = batch_id_set if batch_id_set is not None else set()
            stats.append((tname, len(rows)))
            print(f"  - {tname}: {len(rows)} baris")

        # ── Sinkronkan sequence Postgres ──
        # Seed memakai ID eksplisit, jadi sequence SERIAL masih di angka awal.
        # Tanpa ini, insert baru ke cloud tanpa id eksplisit akan bertabrakan (PK).
        seq_fixed = 0
        for tname in TABLE_ORDER:
            if tname not in cloud_tables:
                continue
            cloud_cols = {c["name"] for c in cloud_insp.get_columns(tname)}
            if "id" not in cloud_cols:
                continue
            seq = cc.execute(
                text(f"SELECT pg_get_serial_sequence('{tname}', 'id')")
            ).scalar()
            if not seq:
                continue
            mx = cc.execute(text(f'SELECT COALESCE(MAX("id"), 1) FROM "{tname}"')).scalar()
            cc.execute(text(f"SELECT setval('{seq}', {mx})"))
            seq_fixed += 1
        print(f"  [sequence disinkronkan di {seq_fixed} tabel]")

    print("\n=== RINGKASAN SEED ===")
    total = 0
    for name, n in stats:
        total += n
        print(f"  {name:35s} {n:>8}")
    print(f"  {'TOTAL':35s} {total:>8}")
    print("\nSeed selesai. ID asli dipertahankan; nilai FK '0'/dangling dinormalisasi ke NULL.")


if __name__ == "__main__":
    main()
