"""cloud_sync.py — Sinkronisasi SATU ARAH: SQLite lokal (essa.db) → cloud (Neon).

Fase 5 panduan (CLOUD_DATABASE_GUIDE.md):
- Aplikasi tetap offline-first; cloud hanya cermin/backup data lokal.
- Dipanggil otomatis saat aplikasi ditutup (closeEvent di main.py).
- Dapat dijalankan manual:  python -m utils.cloud_sync

Metode: DIFF-SYNC per tabel berdasarkan primary key:
  - baris lokal yang belum ada di cloud   -> INSERT
  - baris yang nilainya berbeda           -> UPDATE
  - baris cloud yang tidak ada di lokal   -> DELETE (agar cloud = cermin lokal)
Tidak memerlukan kolom `updated_at` (mayoritas tabel belum memilikinya).

PENORMALISASI:
- Nilai datetime/date dinormalisasi agar perbandingan SQLite vs Postgres
  konsisten. SQLite (via text()/raw SQL) mengembalikan datetime sebagai string
  tanpa mikro-detik ('2026-06-12 13:15:17'), sedangkan Postgres menyimpan
  mikro-detik — keduanya diseragamkan ke format 'YYYY-MM-DD HH:MM:SS.ffffff'.
- Nilai FK yang menunjuk id yang tidak ada (mis. parent_sku_id=0) dinormalisasi
  menjadi None pada perbandingan DAN pada penulisan, sehingga:
    (a) tidak melanggar constraint PostgreSQL, dan
    (b) diff tetap stabil (tidak re-sync terus-menerus).
- Kolom computed (persons.nama_uppercase) tidak pernah ditulis; di Postgres
  kolom generated diisi otomatis oleh server.

PENGAMANAN:
- Tidak pernah melempar exception (aman dipanggil saat app ditutup).
- Jika TOTAL baris lokal = 0 (kemungkinan lokasi database salah), sinkronisasi
  DIHENTIKAN agar data cloud tidak terhapus secara tidak sengaja.
- Semua operasi cloud dalam satu transaksi (all-or-nothing).

Waktu sinkronisasi terakhir disimpan di tabel lokal `app_settings`
(key: cloud_last_sync) dan ikut tersinkron ke cloud.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import MetaData, table as sa_table, column as sa_column, text
from sqlalchemy.dialects import postgresql

from data.database import engine as local_engine, get_cloud_engine
from utils.sync_tables import TABLE_ORDER

_DT_FMT = "%Y-%m-%d %H:%M:%S.%f"


def _norm(v):
    """Normalisasi nilai agar perbandingan SQLite vs Postgres konsisten."""
    if v is None:
        return None
    if isinstance(v, float) and v != v:  # NaN
        return "NaN"
    if isinstance(v, datetime):
        return v.strftime(_DT_FMT)
    if isinstance(v, str):
        s = v.strip()
        # String datetime dari SQLite (tanpa/mengandung mikro-detik) → format kanonik
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).strftime(_DT_FMT)
            except ValueError:
                continue
        return s  # string biasa / tanggal (date) dibiarkan apa adanya
    if hasattr(v, "isoformat"):  # date / time / dll
        return v.isoformat()
    return v


def _build_schema(engine, tables):
    """Refleksikan skema sekali (lebih cepat daripada per-metode inspector):
    {tabel: {cols, pk, fks}}. Kolom computed dikeluarkan dari `cols`."""
    md = MetaData()
    md.reflect(bind=engine, only=tables, resolve_fks=True)
    out = {}
    for t in tables:
        tbl = md.tables.get(t)
        if tbl is None:
            continue
        cols = [c.name for c in tbl.columns if c.computed is None]
        pks = list(tbl.primary_key.columns.keys())
        fks = {}
        for fk in tbl.foreign_keys:
            fks[fk.parent.name] = fk.column.table.name
        out[t] = {"cols": cols, "pk": pks[0] if len(pks) == 1 else None, "fks": fks}
    return out


def _read_rows(conn, tname, cols, pk_col):
    """Baca seluruh baris tabel -> {pk_value: {kolom: nilai}} (dinormalisasi)."""
    sel = ", ".join(f'"{c}"' for c in cols)
    sql = f'SELECT {sel} FROM "{tname}"'
    if pk_col in cols:
        sql += f' ORDER BY "{pk_col}"'
    rows = {}
    for r in conn.execute(text(sql)).mappings():
        d = {c: _norm(r[c]) for c in cols}
        rows[d[pk_col]] = d
    return rows


def _sanitize_row(d, fk_map, tname, id_sets, local_id_set):
    """Normalisasi nilai FK yang menunjuk id yang tidak ada menjadi None."""
    d = dict(d)
    for fk_col, ref_table in fk_map.items():
        val = d.get(fk_col)
        if val is None:
            continue
        ref_ids = local_id_set if ref_table == tname else id_sets.get(ref_table)
        if ref_ids is not None and val not in ref_ids:
            d[fk_col] = None
    return d


def sync_local_to_cloud() -> dict:
    """Sinkronisasi satu arah lokal -> cloud. SELALU mengembalikan dict hasil,
    tidak pernah melempar exception (aman dipanggil saat aplikasi ditutup)."""
    summary = {
        "status": "skipped",
        "message": "CLOUD_DATABASE_URL belum diatur di .env",
        "inserted": 0, "updated": 0, "deleted": 0,
    }
    try:
        cloud_engine = get_cloud_engine()
        if cloud_engine is None:
            return summary

        cloud_schema = _build_schema(cloud_engine, TABLE_ORDER)
        local_schema = _build_schema(local_engine, TABLE_ORDER)

        # ── Tandai waktu sinkronisasi (disimpan lokal, ikut ter-sync) ──
        sync_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with local_engine.begin() as lc:
                lc.execute(text(
                    "INSERT INTO app_settings (key, value, updated_at) "
                    "VALUES ('cloud_last_sync', :ts, :ts) "
                    "ON CONFLICT(key) DO UPDATE SET "
                    "value = excluded.value, updated_at = excluded.updated_at"
                ), {"ts": sync_ts})
        except Exception as e:
            print(f"[CloudSync] (non-kritis) gagal catat waktu sync: {e}")

        counters = {"inserted": 0, "updated": 0, "deleted": 0}
        id_sets = {}          # tname -> set id LOKAL (setelah diproses)
        cloud_id_sets = {}    # tname -> set id di cloud (sebelum sync)
        total_local = 0

        with local_engine.connect() as lc, cloud_engine.begin() as cc:
            # ── PASS 1: INSERT + UPDATE (parent dulu) ──
            for tname in TABLE_ORDER:
                meta = cloud_schema.get(tname)
                if meta is None:
                    continue
                pk = meta["pk"]
                if pk is None:
                    continue
                local_meta = local_schema.get(tname)
                if local_meta is None:
                    continue
                # Kolom yang disinkronkan: milik cloud (non-computed) & lokal
                local_cols = set(local_meta["cols"])
                cols = [c for c in meta["cols"] if c in local_cols]
                if not cols:
                    continue

                local_rows = _read_rows(lc, tname, cols, pk)
                cloud_rows = _read_rows(cc, tname, cols, pk)
                cloud_id_sets[tname] = set(cloud_rows.keys())
                if not local_rows:
                    id_sets[tname] = set()
                    continue
                total_local += len(local_rows)

                fk_map = meta["fks"]
                local_id_set = set(local_rows.keys())

                # Normalisasi kedua sisi (FK 0/dangling -> None) agar diff stabil
                local_norm = {
                    rid: _sanitize_row(d, fk_map, tname, id_sets, local_id_set)
                    for rid, d in local_rows.items()
                }
                cloud_norm = {
                    rid: _sanitize_row(d, fk_map, tname, id_sets, local_id_set)
                    for rid, d in cloud_rows.items()
                }

                to_insert, to_update = [], []
                for rid, ld in local_norm.items():
                    cd = cloud_norm.get(rid)
                    if cd is None:
                        to_insert.append(ld)
                    elif ld != cd:
                        to_update.append(ld)

                if to_insert or to_update:
                    t = sa_table(tname, *[sa_column(c) for c in cols])
                    ins = postgresql.insert(t)
                    stmt = ins.on_conflict_do_update(
                        index_elements=[pk],
                        set_={c: getattr(ins.excluded, c) for c in cols if c != pk},
                    )
                    cc.execute(stmt, to_insert + to_update)
                    counters["inserted"] += len(to_insert)
                    counters["updated"] += len(to_update)

                id_sets[tname] = local_id_set

            # Pengaman: bila total data lokal = 0 (kemungkinan lokasi database salah),
            # JANGAN hapus apa pun dari cloud agar backup tidak ikut terhapus.
            if total_local == 0:
                print("[CloudSync] PERINGATAN: total baris lokal = 0, delete dibatalkan.")

            # ── PASS 2: DELETE (anak dulu — urutan terbalik) ──
            for tname in reversed(TABLE_ORDER):
                meta = cloud_schema.get(tname)
                if meta is None or meta["pk"] is None or tname not in id_sets:
                    continue
                if total_local == 0:
                    continue
                gone = cloud_id_sets.get(tname, set()) - id_sets[tname]
                if gone:
                    t = sa_table(tname, *[sa_column(meta["pk"])])
                    cc.execute(t.delete().where(t.c[meta["pk"]].in_(list(gone))))
                    counters["deleted"] += len(gone)

        summary.update(status="ok", message="sinkronisasi selesai", **counters)
        print(f"[CloudSync] OK - insert={counters['inserted']} "
              f"update={counters['updated']} delete={counters['deleted']}")
        return summary

    except Exception as e:
        print(f"[CloudSync] GAGAL - {e}")
        summary.update(status="error", message=str(e))
        return summary


def main() -> int:
    """Jalankan sinkronisasi dari baris perintah (python -m utils.cloud_sync)."""
    result = sync_local_to_cloud()
    print(f"Status : {result['status']}")
    print(f"Pesan  : {result['message']}")
    print(f"Insert : {result['inserted']} | Update: {result['updated']} | Delete: {result['deleted']}")
    return 0 if result["status"] in ("ok", "skipped") else 1


if __name__ == "__main__":
    sys.exit(main())
