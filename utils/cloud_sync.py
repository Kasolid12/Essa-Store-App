"""cloud_sync.py — Sinkronisasi DUA ARAH penuh LOKAL <-> CLOUD (Neon PostgreSQL).

Fase 5 (push), 5.5 (pull aman), 6.1 (updated_at), 6.2 (ID mapping),
6.3 (kepemilikan perangkat) — lihat CLOUD_DATABASE_GUIDE.md. Ringkasnya:

  - PUSH (lokal -> cloud): setiap perubahan lokal dicerminkan ke cloud.
  - PULL (cloud -> lokal): setiap perubahan cloud dicerminkan ke lokal.
  - Kedua arah berjalan dalam satu operasi (sinkronisasi dua arah), dipicu:
      * otomatis saat aplikasi DIBUKA (thread latar, tidak memblokir) dan
      * otomatis saat aplikasi DITUTUP (closeEvent main.py), serta
      * manual:  python -m utils.cloud_sync            (dua arah penuh)
                 python -m utils.cloud_sync --pull     (auto setup/merge)
                 python -m utils.cloud_sync --pull setup  (perangkat baru)
                 python -m utils.cloud_sync --pull merge  (gabung manual)

LAPISAN ID MAPPING (Fase 6 bagian 2) — tabel lokal `sync_id_map`:
  Masalah: dua perangkat masing-masing memakai id autoincrement mulai dari 1,
  sehingga id yang sama bisa menunjuk baris yang BERBEDA di dua perangkat.
  Solusi: tabel `sync_id_map` (hanya lokal, TIDAK pernah disinkronkan) menyimpan
  pemetaan id lokal -> id cloud per tabel:
      (table_name, local_id) -> cloud_id, deleted_at (tombstone), last_seen

  - Baris baru lokal dengan id yang masih bebas di cloud -> memakai id SAMA
    (identity mapping).
  - Baris baru lokal dengan id yang sudah dipakai baris lain di cloud -> diberi
    id cloud BARU (sequence Postgres / MAX+1), pemetaan dicatat di sync_id_map.
  - Nilai FK antar tabel DITERJEMAHKAN lewat pemetaan (induk diproses lebih
    dulu, jadi terjemahan induk selalu tersedia saat anak diproses).
  - Saat perangkat baru mengunduh data, baris cloud diberi id lokal = id cloud
    bila bebas, atau id lokal baru bila bertabrakan (pemetaan tetap dicatat).

RESOLUSI KONFLIK (last-write-wins via `updated_at`):
  - Nilai NULL dianggap paling lama (baris lama). Timestamp dibandingkan sebagai
    string kanonik ('YYYY-MM-DD HH:MM:SS.ffffff') sehingga konsisten lintas DB.
  - updated_at sama & nilai berbeda -> "perangkat yang sedang dipakai menang"
    (nilai lokal dikirim ke cloud) — konsisten dengan filosofi Fase 5.5.
  - Baris yang nilainya sama (selain updated_at) dianggap baris yang sama.

KEPEMILIKAN BARIS (Fase 6.3) — kolom created_by_device / updated_by_device:
  - Aplikasi mengisi kolom ini otomatis (event ORM di data/models/base.py):
    created_by_device saat INSERT, updated_by_device setiap UPDATE.
  - Sync memakai created_by_device untuk memutuskan "baris yang sama vs
    tabrakan" secara PASTI di langkah 1 (menggantikan heuristik isi untuk
    baris yang sudah punya pemilik): milik perangkat ini -> identity;
    milik perangkat lain -> tabrakan (id cloud baru); NULL (baris lama) ->
    heuristik isi lama. Kepemilikan TIDAK pernah berubah lewat UPDATE.

DELETE (dua arah, berbasis pemetaan + tombstone):
  - Perangkat HANYA menghapus baris cloud yang ADA PEMETAANNYA di perangkat itu.
    Baris milik perangkat lain yang belum pernah ditarik TIDAK akan terhapus.
  - Saat baris lokal dihapus, mapping diberi deleted_at (tombstone) dan baris
    cloud ikut dihapus — KECUALI cloud sudah berubah setelah sync terakhir
    (perangkat lain mengeditnya → edit itu yang menang, tombstone ditahan).
  - Saat baris cloud dihapus perangkat lain, baris lokal dicerminkan (dihapus) —
    KECUALI perangkat ini mengedit barisnya setelah sync terakhir (edit lokal
    yang menang → baris di-cloud "dihidupkan kembali").
  - Bila total baris lokal = 0 (kemungkinan lokasi database salah), penghapusan
    cloud DIBATALKAN agar backup tidak ikut terhapus.

PENORMALISASI nilai (sama seperti Fase 5):
  - datetime/date dinormalisasi agar perbandingan SQLite vs Postgres konsisten.
  - FK yang menunjuk id yang tidak dikenal dinormalisasi menjadi None.

TIDAK PERNAH melempar exception (aman dipanggil saat aplikasi ditutup);
semua operasi cloud & lokal dalam satu transaksi (all-or-nothing).
"""
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import MetaData, table as sa_table, column as sa_column, text
from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from data.database import engine as local_engine, get_cloud_engine
from utils.sync_tables import TABLE_ORDER

_DT_FMT = "%Y-%m-%d %H:%M:%S.%f"
_EPOCH = "0000-00-00 00:00:00.000000"   # representasi "paling lama" untuk LWW

_DEVICE_COLS = ("created_by_device", "updated_by_device")  # meta kepemilikan
_META_COLS = ("updated_at",) + _DEVICE_COLS                 # untuk _same_content

_ID_MAP_DDL = """
CREATE TABLE IF NOT EXISTS sync_id_map (
    table_name TEXT NOT NULL,
    local_id   INTEGER NOT NULL,
    cloud_id   INTEGER NOT NULL,
    deleted_at TEXT,
    last_seen  TEXT,
    PRIMARY KEY (table_name, local_id)
)
"""


# ─────────────────────────────────────────────────────────────────────
# Utilitas nilai / skema
# ─────────────────────────────────────────────────────────────────────

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
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).strftime(_DT_FMT)
            except ValueError:
                continue
        return s
    if hasattr(v, "isoformat"):  # date / time / dll
        return v.isoformat()
    return v


def _ts(v) -> str:
    """Ubah nilai timestamp menjadi string kanonik yang bisa dibandingkan.
    None (belum pernah diisi) dianggap paling lama (epoch)."""
    if v is None:
        return _EPOCH
    n = _norm(v)
    return n if isinstance(n, str) else str(n)


def _build_schema(engine, tables):
    """Refleksikan skema sekali: {tabel: {cols, pk, fks}}. Kolom computed
    dikeluarkan dari `cols` (di Postgres diisi otomatis oleh server)."""
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


def _translate_row(d, fk_map, tname, trans):
    """Terjemahkan nilai FK ke id tujuan (cloud atau lokal) lewat peta `trans`
    ({tabel: {id_asli: id_tujuan}}). FK menunjuk id yang tidak dikenal di-null-kan.
    Bila tabel referensi belum ada di `trans` (mis. self-FK saat perbandingan
    awal), nilai dibiarkan apa adanya."""
    d = dict(d)
    for fk_col, ref in fk_map.items():
        v = d.get(fk_col)
        if v is None:
            continue
        tmap = trans.get(ref)
        if tmap is None:
            continue  # tabel belum dipetakan — biarkan (dipakai saat perbandingan)
        d[fk_col] = tmap.get(v)  # None bila parent tidak dikenal -> di-null-kan
    return d


def _same_content(a, b, pk=None) -> bool:
    """True bila dua baris sama persis, mengabaikan kolom pk, `updated_at`,
    dan kolom kepemilikan perangkat (created_by_device/updated_by_device) —
    meta yang boleh berbeda secara sah pada baris yang sama (pk berbeda
    secara sah untuk baris yang di-remap id cloud-nya)."""
    ka = {k: v for k, v in a.items() if k not in _META_COLS and k != pk}
    kb = {k: v for k, v in b.items() if k not in _META_COLS and k != pk}
    return ka == kb


def _row_comp(d, pk) -> dict:
    """Baris untuk perbandingan nilai — tanpa kolom pk & meta kepemilikan
    (created_by_device/updated_by_device). `updated_at` TETAP dibandingkan
    karena dipakai last-write-wins."""
    return {k: v for k, v in d.items() if k != pk and k not in _DEVICE_COLS}


def _without_owner(d) -> dict:
    """Salinan baris TANPA created_by_device — kepemilikan HANYA diatur saat
    INSERT; tidak boleh tertimpa oleh update (apalagi NULL dari baris lama)."""
    return {k: v for k, v in d.items() if k != "created_by_device"}


def _decide_identity(ld, cr, cmp_ld, cmp_cr, pk, my_device_id) -> bool:
    """Putuskan apakah baris lokal (belum terpetakan) adalah baris yang SAMA
    dengan baris cloud di id yang sama (identity) atau baris BERBEDA (tabrakan).

    Fase 6.3 — kepemilikan PASTI lewat created_by_device:
      - cloud milik perangkat ini  -> identity (baris buatan kita).
      - cloud milik perangkat LAIN -> tabrakan, KECUALI baris lokal juga belum
        punya kepemilikan (NULL, mis. salinan DB lama) dan isinya identik —
        aman digabung daripada diduplikasi.
      - cloud belum punya kepemilikan (NULL, baris lama) -> heuristik isi lama
        (konten sama ATAU hanya satu sisi yang punya updated_at).
    """
    owner = cr.get("created_by_device")
    if owner is None:
        # baris lama di cloud: pertahankan perilaku heuristik Fase 6.2
        return _same_content(cmp_ld, cmp_cr, pk) or _one_side_updated(ld, cr)
    if owner == my_device_id:
        return True
    if ld.get("created_by_device") is None:
        # baris lokal lama + isi identik -> kemungkinan salinan DB lama
        return _same_content(cmp_ld, cmp_cr, pk)
    return False  # dua baris berbeda yang kebetulan sama id-nya


def _one_side_updated(a, b) -> bool:
    """True bila tepat satu sisi memiliki updated_at (sisi itu lebih baru)."""
    return (a.get("updated_at") is None) != (b.get("updated_at") is None)


# ─────────────────────────────────────────────────────────────────────
# Klasifikasi error jaringan/DNS (untuk retry & pesan ramah)
# ─────────────────────────────────────────────────────────────────────

# Pola error SEMENTARA (dapat hilang sendiri) — DNS/network/timeout.
# Error ini layak dicoba ulang otomatis; error lain (kredensial, skema)
# tidak akan sembuh dengan retry sehingga langsung dilaporkan.
_TRANSIENT_MARKERS = (
    "translate host name",          # DNS gagal memetakan host Neon
    "name or service not known",
    "temporary failure in name resolution",
    "getaddrinfo failed",
    "could not connect",
    "connection refused",
    "connection timed out",
    "timed out",
    "network is unreachable",
    "no route to host",
    "connection reset",
    "broken pipe",
    "server closed the connection",
)


def _is_transient(msg: str) -> bool:
    """True bila pesan error termasuk kegagalan jaringan/DNS sementara."""
    m = (msg or "").lower()
    return any(k in m for k in _TRANSIENT_MARKERS)


def _friendly_error(msg: str) -> str:
    """Ubah pesan error SQLAlchemy mentah menjadi kalimat ramah (Indonesia).
    Bila polanya tidak dikenal, kembalikan pesan aslinya (masih informatif)."""
    m = (msg or "").lower()
    if any(k in m for k in ("translate host name", "name or service not known",
                            "temporary failure in name resolution", "getaddrinfo failed")):
        return ("Cloud tidak dapat dijangkau: DNS gagal memetakan host Neon "
                "(jaringan/ISP belum siap atau hostname salah). Data lokal AMAN — "
                "sync dicoba ulang otomatis; klik SYNC NOW nanti. Bila terus "
                "berulang, periksa kembali CLOUD_DATABASE_URL di file .env.")
    if any(k in m for k in ("could not connect", "connection refused", "timed out",
                            "network is unreachable")):
        return ("Cloud tidak dapat dijangkau: koneksi ke Neon gagal/timeout. "
                "Periksa koneksi internet, lalu klik SYNC NOW.")
    if "password authentication failed" in m or "authentication failed" in m:
        return ("Cloud gagal: kredensial ditolak — periksa password pada "
                "CLOUD_DATABASE_URL di file .env.")
    if "does not exist" in m and ("database" in m or "role" in m):
        return ("Cloud gagal: database/role tidak ditemukan — periksa nama "
                "database pada CLOUD_DATABASE_URL di file .env.")
    return msg


def _record_cloud_last_error(msg: str):
    """Catat kegagalan sync terakhir ke app_settings lokal (dibaca status UI).
    Tidak pernah melempar — status indikator hanyalah tambahan."""
    try:
        with local_engine.connect() as lc:
            _record_app_setting(lc, "cloud_last_error", msg)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────
# Tabel pemetaan id (sync_id_map) — lokal saja
# ─────────────────────────────────────────────────────────────────────

def _ensure_id_map_table(lc):
    lc.execute(text(_ID_MAP_DDL))
    lc.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_sync_id_map_cloud "
            "ON sync_id_map (table_name, cloud_id)"
        )
    )


def _read_map(lc, tname):
    """{local_id: {cid, deleted_at, last_seen}} untuk satu tabel."""
    out = {}
    for r in lc.execute(
        text(
            "SELECT local_id, cloud_id, deleted_at, last_seen "
            "FROM sync_id_map WHERE table_name = :t"
        ),
        {"t": tname},
    ):
        out[r[0]] = {"cid": r[1], "deleted_at": r[2], "last_seen": r[3]}
    return out


def _map_upsert(lc, tname, lid, cid, deleted_at, last_seen):
    lc.execute(
        text(
            "INSERT INTO sync_id_map (table_name, local_id, cloud_id, deleted_at, last_seen) "
            "VALUES (:t, :l, :c, :d, :s) "
            "ON CONFLICT(table_name, local_id) DO UPDATE SET "
            "cloud_id = excluded.cloud_id, "
            "deleted_at = excluded.deleted_at, "
            "last_seen = excluded.last_seen"
        ),
        {"t": tname, "l": lid, "c": cid, "d": deleted_at, "s": last_seen},
    )


def _map_remove(lc, tname, lid):
    lc.execute(
        text("DELETE FROM sync_id_map WHERE table_name = :t AND local_id = :l"),
        {"t": tname, "l": lid},
    )


# ─────────────────────────────────────────────────────────────────────
# app_settings & identitas perangkat
# ─────────────────────────────────────────────────────────────────────

def _record_app_setting(conn, key, value):
    """Upsert key-value ke app_settings (didukung SQLite & Postgres)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        text(
            "INSERT INTO app_settings (key, value, updated_at) "
            "VALUES (:key, :val, :ts) "
            "ON CONFLICT(key) DO UPDATE SET "
            "value = excluded.value, updated_at = excluded.updated_at"
        ),
        {"key": key, "val": str(value), "ts": ts},
    )


def _get_device_id(conn) -> str:
    """Ambil atau buat device_id unik per perangkat."""
    row = conn.execute(
        text("SELECT value FROM app_settings WHERE key = 'device_id'")
    ).scalar()
    if row:
        return row
    dev = uuid4().hex[:8].upper()
    _record_app_setting(conn, "device_id", dev)
    return dev


def _local_has_data(local_schema) -> bool:
    """True bila ada baris DATA (bukan metadata app_settings) di DB lokal."""
    with local_engine.connect() as lc:
        for tname, meta in local_schema.items():
            if meta is None or meta.get("pk") is None:
                continue
            if tname == "app_settings":
                continue
            try:
                n = lc.execute(text(f'SELECT COUNT(*) FROM "{tname}"')).scalar()
            except Exception:
                continue
            if n:
                return True
    return False


def _push_app_settings(lc, cc):
    """Push metadata app_settings lokal -> cloud (device_id, heartbeat)."""
    rows = lc.execute(
        text("SELECT key, value, updated_at FROM app_settings")
    ).mappings().all()
    for r in rows:
        cc.execute(
            text(
                "INSERT INTO app_settings (key, value, updated_at) "
                "VALUES (:key, :val, :ts) "
                "ON CONFLICT(key) DO UPDATE SET "
                "value = excluded.value, updated_at = excluded.updated_at"
            ),
            {
                "key": r["key"],
                "val": str(r["value"]) if r["value"] is not None else "",
                "ts": r["updated_at"] or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )


# ─────────────────────────────────────────────────────────────────────
# Alokasi id cloud baru (tabrakan id antar perangkat)
# ─────────────────────────────────────────────────────────────────────

def _new_cloud_id(cc, tname, used):
    """Alokasikan id cloud BARU untuk baris yang bertabrakan. Id dijamin unik
    dalam satu run (lewat set `used`); lintas run dijamin oleh sequence/max."""
    mx = int(cc.execute(text(f'SELECT COALESCE(MAX("id"), 0) FROM "{tname}"')).scalar() or 0)
    cand = max(mx, max(used, default=0)) + 1
    used.add(cand)
    return cand


def _fix_cloud_sequences(cloud_engine, cloud_schema, plans):
    """Setelah transaksi sukses: selaraskan sequence Postgres agar insert
    eksplisit (id asli / id baru) tidak membuat auto-id bertabrakan di masa
    depan. Hanya untuk Postgres; SQLite-tiruan (uji) dilewati."""
    if cloud_engine.dialect.name != "postgresql":
        return
    with cloud_engine.connect() as cc:
        for tname, plan in plans.items():
            if not plan["ci"]:
                continue
            seq = cc.execute(
                text("SELECT pg_get_serial_sequence(:t, 'id')"), {"t": tname}
            ).scalar()
            if not seq:
                continue
            mx = cc.execute(text(f'SELECT COALESCE(MAX("id"), 1) FROM "{tname}"')).scalar()
            cc.execute(text(f"SELECT setval('{seq}', {mx})"))


# ─────────────────────────────────────────────────────────────────────
# Penulisan ke DB (eksekusi hasil perencanaan)
# ─────────────────────────────────────────────────────────────────────

def _upsert_into_local(lc, tname, cols, pk, rows):
    """Insert/update serentak ke SQLite lokal (ON CONFLICT DO UPDATE)."""
    t = sa_table(tname, *[sa_column(c) for c in cols])
    ins = sqlite_dialect.insert(t)
    stmt = ins.on_conflict_do_update(
        index_elements=[pk],
        set_={c: getattr(ins.excluded, c) for c in cols if c != pk},
    )
    lc.execute(stmt, rows)


def _execute_cloud(cc, tname, cols, pk, plan):
    """INSERT + UPDATE ke cloud (id sudah pasti baru — insert polos).
    Konflik index unik (mis. kode_sku duplikat antar perangkat) dilewati
    per-baris via savepoint dengan peringatan, agar satu baris bermasalah
    tidak menggagalkan seluruh sinkronisasi.
    Mengembalikan (set lid gagal-insert, set cid gagal-update)."""
    ci_fail, cu_fail = set(), set()
    if not (plan["ci"] or plan["cu"]):
        return ci_fail, cu_fail
    t = sa_table(tname, *[sa_column(c) for c in cols])
    for lid, cid, row in plan["ci"]:
        try:
            with cc.begin_nested():
                cc.execute(t.insert().values(row))
        except IntegrityError as e:
            ci_fail.add(lid)
            print(f"[CloudSync] PERINGATAN: insert {tname} (lid={lid}, cloud={cid}) "
                  f"dilewati — konflik index unik: {e.orig}")
    for cid, row in plan["cu"]:
        vals = {k: v for k, v in row.items() if k != pk}
        try:
            with cc.begin_nested():
                cc.execute(t.update().where(t.c[pk] == cid).values(vals))
        except IntegrityError as e:
            cu_fail.add(cid)
            print(f"[CloudSync] PERINGATAN: update {tname} cloud={cid} dilewati — "
                  f"konflik index unik: {e.orig}")
    return ci_fail, cu_fail


def _execute_local(lc, tname, cols, pk, plan):
    """INSERT + UPDATE ke SQLite lokal (upsert idempoten). Konflik index unik
    lokal dilewati per-baris via savepoint dengan peringatan.
    Mengembalikan (set lid gagal-insert, set lid gagal-update)."""
    li_fail, lu_fail = set(), set()
    if not (plan["li"] or plan["lu"]):
        return li_fail, lu_fail
    for lid, row in plan["li"]:
        try:
            with lc.begin_nested():
                _upsert_into_local(lc, tname, cols, pk, [row])
        except IntegrityError as e:
            li_fail.add(lid)
            print(f"[CloudSync] PERINGATAN: pull {tname} (cloud={row.get(pk)}, lid={lid}) "
                  f"dilewati — konflik index unik lokal: {e.orig}")
    for lid, row in plan["lu"]:
        try:
            with lc.begin_nested():
                _upsert_into_local(lc, tname, cols, pk, [row])
        except IntegrityError as e:
            lu_fail.add(lid)
            print(f"[CloudSync] PERINGATAN: update lokal {tname} lid={lid} dilewati — "
                  f"konflik index unik lokal: {e.orig}")
    return li_fail, lu_fail


def _execute_deletes(cc, lc, tname, pk, plan):
    """DELETE cloud & lokal. Konflik (mis. FK masih dipakai) dilewati per-id via
    savepoint dengan peringatan. Mengembalikan (set cid gagal, set lid gagal)."""
    cd_fail, ld_fail = set(), set()
    if plan["cd"]:
        t = sa_table(tname, *[sa_column(pk)])
        for cid in plan["cd"]:
            try:
                with cc.begin_nested():
                    cc.execute(t.delete().where(t.c[pk] == cid))
            except IntegrityError as e:
                cd_fail.add(cid)
                print(f"[CloudSync] PERINGATAN: delete cloud {tname} id={cid} dilewati: {e.orig}")
    if plan["ld"]:
        t = sa_table(tname, *[sa_column(pk)])
        for lid in plan["ld"]:
            try:
                with lc.begin_nested():
                    lc.execute(t.delete().where(t.c[pk] == lid))
            except IntegrityError as e:
                ld_fail.add(lid)
                print(f"[CloudSync] PERINGATAN: delete lokal {tname} id={lid} dilewati: {e.orig}")
    return cd_fail, ld_fail


def _execute_maps(lc, tname, plan):
    for lid, cid, deleted_at, last_seen in plan["mu"]:
        _map_upsert(lc, tname, lid, cid, deleted_at, last_seen)
    for lid in plan["mr"]:
        _map_remove(lc, tname, lid)


# ─────────────────────────────────────────────────────────────────────
# Perencanaan per tabel (logika dua arah + ID mapping)
# ─────────────────────────────────────────────────────────────────────

def _plan_table(lc, cc, tname, lmeta, cmeta, l2c, c2l, used_ids, now, my_device_id):
    """Hitung SEMUA aksi untuk satu tabel (tidak menulis apa pun).

    `l2c`/`c2l` = terjemahan tabel INDUK yang sudah diproses (lokal->cloud dan
    cloud->lokal). `my_device_id` dipakai keputusan kepemilikan (Fase 6.3).
    Mengembalikan plan:
      ci [(cid, row)]  cu [(cid, row)]  cd [cid]        ← sisi cloud
      li [(lid, row)]  lu [(lid, row)]  ld [lid]        ← sisi lokal
      mu [(lid,cid,deleted_at,last_seen)]  mr [lid]     ← pemetaan
      l2c_t / c2l_t / total_local
    """
    plan = {
        "ci": [], "cu": [], "cd": [],
        "li": [], "lu": [], "ld": [],
        "mu": [], "mr": [],
        "l2c_t": {}, "c2l_t": {}, "total_local": 0,
    }
    if cmeta is None or lmeta is None or cmeta["pk"] is None:
        return plan
    pk = cmeta["pk"]
    fk_map = cmeta["fks"]
    cols = [c for c in cmeta["cols"] if c in set(lmeta["cols"])]
    if not cols:
        return plan

    local_rows = _read_rows(lc, tname, cols, pk)
    cloud_rows = _read_rows(cc, tname, cols, pk)
    maps = _read_map(lc, tname)
    plan["total_local"] = len(local_rows)

    # ── Langkah 1: putuskan identitas baris lokal yang belum terpetakan ──
    #    Kepemilikan (Fase 6.3) menentukan: milik perangkat ini -> identity;
    #    milik perangkat lain -> tabrakan -> id cloud baru. Baris lama (NULL)
    #    memakai heuristik isi (konten sama / hanya updated_at yang beda).
    # Peta sementara untuk perbandingan baris yang sama: self-FK (mis. nilai
    # 0 = "tanpa induk" pada data lama) dinormalisasi seperti sisi cloud
    # (0 -> None), sehingga baris yang sebenarnya SAMA tidak dianggap tabrakan.
    provisional = {**l2c, tname: {lid: lid for lid in local_rows}}
    new_lid2cid = {}  # lid -> cid untuk baris yang akan di-INSERT ke cloud
    for lid, ld in local_rows.items():
        if lid in maps:
            continue
        if lid in cloud_rows:
            cr = cloud_rows[lid]
            cmp_ld = _translate_row(ld, fk_map, tname, provisional)
            cmp_cr = _translate_row(cr, fk_map, tname, provisional)
            if _decide_identity(ld, cr, cmp_ld, cmp_cr, pk, my_device_id) \
                    and lid not in used_ids:
                # baris yang sama (identity mapping)
                maps[lid] = {"cid": lid, "deleted_at": None, "last_seen": now}
            else:
                # tabrakan id -> baris ini mendapat id cloud BARU
                new_lid2cid[lid] = _new_cloud_id(cc, tname, used_ids)
        else:
            if lid in used_ids:
                # id ini sudah dipakai remap lain di run yang sama -> alokasikan baru
                new_lid2cid[lid] = _new_cloud_id(cc, tname, used_ids)
            else:
                new_lid2cid[lid] = lid  # id bebas di cloud -> identity insert

    # ── l2c_t & c2l_t: pemetaan penuh tabel ini (untuk terjemahan FK) ──
    l2c_t = {}
    c2l_t = {}
    for lid in local_rows:
        if lid in maps:
            l2c_t[lid] = maps[lid]["cid"]
            c2l_t[maps[lid]["cid"]] = lid
        elif lid in new_lid2cid:
            l2c_t[lid] = new_lid2cid[lid]
            c2l_t[new_lid2cid[lid]] = lid
    plan["l2c_t"] = l2c_t
    plan["c2l_t"] = c2l_t
    full_l2c = {**l2c, tname: l2c_t}
    full_c2l = {**c2l, tname: c2l_t}

    # ── Langkah 2: baris lokal baru -> INSERT ke cloud ──
    for lid, cid in new_lid2cid.items():
        ld = _translate_row(local_rows[lid], fk_map, tname, full_l2c)
        ld[pk] = cid
        plan["ci"].append((lid, cid, ld))
        plan["mu"].append((lid, cid, None, now))

    # ── Langkah 3: baris terpetakan, lokal MASIH ada ──
    for lid, m in list(maps.items()):
        if lid not in local_rows:
            continue
        cid = m["cid"]
        ld = _translate_row(local_rows[lid], fk_map, tname, full_l2c)
        cr = cloud_rows.get(cid)
        if cr is None:
            # Cloud menghapusnya. Bila perangkat ini mengedit setelah sync
            # terakhir, edit lokal menang -> hidupkan kembali di cloud.
            if _ts(ld.get("updated_at")) > _ts(m["last_seen"]):
                ld[pk] = cid  # hidupkan kembali DI id cloud yang sama
                plan["ci"].append((lid, cid, ld))
                plan["mu"].append((lid, cid, None, now))
            else:
                plan["ld"].append(lid)   # mirror: cloud menghapus -> lokal ikut
                plan["mr"].append(lid)
            continue
        if _row_comp(ld, pk) == _row_comp(cr, pk):
            plan["mu"].append((lid, cid, None, now))  # sama -> refresh last_seen
            continue
        # last-write-wins via updated_at (NULL dianggap paling lama)
        if _ts(ld.get("updated_at")) > _ts(cr.get("updated_at")):
            # push lokal; created_by_device TIDAK ikut (kepemilikan tetap)
            plan["cu"].append((cid, _without_owner(ld)))
        elif _ts(cr.get("updated_at")) > _ts(ld.get("updated_at")):
            # tarik ke id LOKAL (lid) — jangan pakai pk cloud (cid), karena baris
            # hasil remap punya id lokal berbeda dari id cloud.
            lr = dict(cr)
            lr[pk] = lid
            plan["lu"].append((lid, lr))        # cloud lebih baru -> tarik
        else:
            # seri -> perangkat yang dipakai menang (created_by_device tetap)
            plan["cu"].append((cid, _without_owner(ld)))
        plan["mu"].append((lid, cid, None, now))

    # ── Langkah 4: baris terpetakan, lokal sudah DIHAPUS (tombstone) ──
    for lid, m in list(maps.items()):
        if lid in local_rows:
            continue
        cid = m["cid"]
        cr = cloud_rows.get(cid)
        if cr is None:
            plan["mr"].append(lid)              # cloud sudah tidak ada -> bersihkan
            continue
        # Cloud diedit perangkat lain SETELAH penghapusan lokal -> edit itu menang,
        # tombstone ditahan (dicoba lagi di sync berikutnya).
        if _ts(cr.get("updated_at")) > _ts(m["deleted_at"] or m["last_seen"]):
            plan["mu"].append((lid, cid, m["deleted_at"] or now, now))
            continue
        plan["cd"].append(cid)                  # kita hapus -> cloud ikut terhapus
        plan["mr"].append(lid)

    # ── Langkah 5: baris cloud BARU (belum dikenal) -> INSERT lokal ──
    known_cloud = {m["cid"] for m in maps.values()}   # termasuk tombstone
    local_max = max(local_rows.keys()) if local_rows else 0
    for cid, cr in cloud_rows.items():
        if cid in known_cloud or cid in c2l_t:
            continue
        if cid in local_rows or cid in new_lid2cid:
            lid = local_max + 1                 # id lokal dipakai baris lain
            local_max += 1
        else:
            lid = cid                           # bebas -> identity lokal
        lc_row = _translate_row(
            cr, fk_map, tname, {**full_c2l, tname: {**c2l_t, cid: lid}}
        )
        lc_row[pk] = lid
        plan["li"].append((lid, lc_row))
        plan["mu"].append((lid, cid, None, now))
        # Baris yang ditarik ikut masuk peta terjemahan — penting agar FK anak
        # (tabel berikutnya) menunjuk id lokal yang benar, bukan None.
        c2l_t[cid] = lid
        l2c_t[lid] = cid

    plan["l2c_t"] = l2c_t
    plan["c2l_t"] = c2l_t
    return plan


# ─────────────────────────────────────────────────────────────────────
# Inti sinkronisasi dua arah
# ─────────────────────────────────────────────────────────────────────

def _run_sync_once(mode: str = "sync") -> dict:
    """Jalankan SATU percobaan sinkronisasi DUA ARAH penuh (tanpa retry).
    Mengembalikan dict hasil; pada gagal TIDAK mencetak pesan (dilakukan
    pemanggil `_run_sync`) agar retry tidak membanjiri console."""
    summary = {
        "status": "skipped",
        "message": "CLOUD_DATABASE_URL belum diatur di .env",
        "mode": mode,
        "inserted": 0, "updated": 0, "deleted": 0,
        "pulled": 0, "updated_local": 0, "deleted_local": 0,
    }
    try:
        cloud_engine = get_cloud_engine()
        if cloud_engine is None:
            return summary

        # Pastikan skema lokal ada (sama dengan create_all saat aplikasi start).
        from data.models.base import Base as _Base
        import data.models  # noqa: F401
        _Base.metadata.create_all(bind=local_engine)

        cloud_schema = _build_schema(cloud_engine, TABLE_ORDER)
        local_schema = _build_schema(local_engine, TABLE_ORDER)

        if mode == "auto":
            mode = "setup" if not _local_has_data(local_schema) else "sync"
        if mode == "setup" and _local_has_data(local_schema):
            summary.update(
                status="skipped",
                message="mode setup butuh DB lokal kosong (gunakan 'merge' bila lokal berisi data)",
                mode=mode,
            )
            return summary

        now = datetime.now().strftime(_DT_FMT)
        counters = {
            "inserted": 0, "updated": 0, "deleted": 0,
            "pulled": 0, "updated_local": 0, "deleted_local": 0,
        }
        l2c, c2l, allocated, plans = {}, {}, {}, {}
        total_local = 0

        with local_engine.begin() as lc, cloud_engine.begin() as cc:
            _ensure_id_map_table(lc)
            my_device_id = _get_device_id(lc)  # dibuat sebelum operasi apa pun
            # Beri tahu model: tulis ORM apa pun (mis. dari thread lain) ikut
            # mengisi created_by_device/updated_by_device dengan id perangkat ini.
            import data.models.base as _models_base
            _models_base.CURRENT_DEVICE_ID = my_device_id

            # ── PERENCANAAN: induk dulu (urutan TABLE_ORDER) ──
            for tname in TABLE_ORDER:
                if tname == "app_settings":
                    continue  # metadata: tidak masuk lapisan ID mapping
                cmeta = cloud_schema.get(tname)
                lmeta = local_schema.get(tname)
                if cmeta is None or lmeta is None:
                    continue
                allocated[tname] = set()
                plan = _plan_table(
                    lc, cc, tname, lmeta, cmeta, l2c, c2l,
                    allocated[tname], now, my_device_id,
                )
                plans[tname] = plan
                total_local += plan["total_local"]
                l2c[tname] = plan["l2c_t"]   # siap untuk anak (FK)
                c2l[tname] = plan["c2l_t"]

            # ── EKSEKUSI tulis (induk dulu; cloud & lokal independen) ──
            for tname, plan in plans.items():
                cmeta = cloud_schema[tname]
                lmeta = local_schema[tname]
                pk = cmeta["pk"]
                cols = [c for c in cmeta["cols"] if c in set(lmeta["cols"])]
                ci_fail, cu_fail = _execute_cloud(cc, tname, cols, pk, plan)
                li_fail, lu_fail = _execute_local(lc, tname, cols, pk, plan)
                # Baris yang gagal di-insert JANGAN dicatat pemetaannya (agar
                # tidak dianggap "dihapus cloud" pada run berikutnya).
                plan["_map_fail"] = ci_fail | li_fail
                counters["inserted"] += len(plan["ci"]) - len(ci_fail)
                counters["updated"] += len(plan["cu"]) - len(cu_fail)
                counters["pulled"] += len(plan["li"]) - len(li_fail)
                counters["updated_local"] += len(plan["lu"]) - len(lu_fail)

            # ── EKSEKUSI hapus (anak dulu) + simpan pemetaan ──
            for tname in reversed(list(plans.keys())):
                plan = plans[tname]
                pk = cloud_schema[tname]["pk"]
                if total_local == 0 and plan["cd"]:
                    # Lokasi DB lokal kemungkinan salah -> jangan hapus backup cloud
                    plan["cd"] = []
                cd_fail, ld_fail = _execute_deletes(cc, lc, tname, pk, plan)
                plan["mu"] = [
                    m for m in plan["mu"] if m[0] not in plan.get("_map_fail", set())
                ]
                _execute_maps(lc, tname, plan)
                counters["deleted"] += len(plan["cd"]) - len(cd_fail)
                counters["deleted_local"] += len(plan["ld"]) - len(ld_fail)

            # ── Metadata: push app_settings + heartbeat lokal ──
            # Bersihkan catatan kegagalan dulu (status UI kembali normal) BARU
            # push — agar cloud tidak membawa error lama satu siklus lagi.
            _record_app_setting(lc, "cloud_last_error", "")
            _record_app_setting(lc, "device_id", my_device_id)
            _record_app_setting(lc, "cloud_last_sync", now)
            _record_app_setting(lc, "cloud_last_pull", now)
            _push_app_settings(lc, cc)

        # Transaksi sukses -> selaraskan sequence cloud (postgres saja).
        _fix_cloud_sequences(cloud_engine, cloud_schema, plans)

        summary.update(
            status="ok",
            message="sinkronisasi dua arah selesai",
            mode=mode,
            inserted=counters["inserted"],
            updated=counters["updated"],
            deleted=counters["deleted"],
            pulled=counters["pulled"],
            updated_local=counters["updated_local"],
            deleted_local=counters["deleted_local"],
        )
        print(
            f"[CloudSync] OK ({mode}) - cloud: insert={counters['inserted']} "
            f"update={counters['updated']} delete={counters['deleted']} | "
            f"lokal: pull={counters['pulled']} update={counters['updated_local']} "
            f"delete={counters['deleted_local']}"
        )
        return summary

    except Exception as e:
        summary.update(status="error", message=str(e))
        return summary


# ─────────────────────────────────────────────────────────────────────
# Wrapper dengan retry otomatis (error jaringan/DNS sementara)
# ─────────────────────────────────────────────────────────────────────

def _run_sync(mode: str = "sync", retries: int = 2) -> dict:
    """Jalankan sinkronisasi DUA ARAH penuh dengan retry otomatis.
    SELALU mengembalikan dict hasil; TIDAK pernah melempar exception.

    mode:
      - "sync" : dua arah (dipakai saat app ditutup & CLI default)
      - "auto" : setup bila lokal kosong, selain itu dua arah
      - "setup": dua arah, tapi ditolak bila lokal sudah berisi data
      - "merge": dua arah (gabung manual)

    retries: berapa kali dicoba ulang bila gagal karena JARINGAN/DNS
      sementara (mis. Wi-Fi belum siap saat PC baru dinyalakan). Error
      non-jaringan (kredensial, skema) langsung dilaporkan tanpa retry.
      `retries=0` dipakai jalur penutupan aplikasi agar tidak menunda
      keluar aplikasi saat offline.
    """
    attempt = 0
    while True:
        attempt += 1
        result = _run_sync_once(mode)
        if result["status"] != "error" or not _is_transient(result["message"]) \
                or attempt > retries:
            if result["status"] == "error":
                friendly = _friendly_error(result["message"])
                print(f"[CloudSync] GAGAL - {friendly}")
                _record_cloud_last_error(friendly)
                result["message"] = friendly
            return result
        print(
            f"[CloudSync] Jaringan tidak stabil — percobaan ulang "
            f"{attempt}/{retries}..."
        )
        time.sleep(2.5)


# ─────────────────────────────────────────────────────────────────────
# API publik
# ─────────────────────────────────────────────────────────────────────

def ensure_device_id() -> str:
    """Pastikan device_id lokal ada di app_settings & set CURRENT_DEVICE_ID
    (Fase 6.3) agar semua tulis ORM mengisi created_by_device / updated_by_device
    otomatis. Dipanggil saat aplikasi start — aman walau cloud tidak diatur.
    Melempar exception bila tabel app_settings belum ada (caller menangani)."""
    with local_engine.connect() as lc:
        dev = _get_device_id(lc)
    import data.models.base as _models_base
    _models_base.CURRENT_DEVICE_ID = dev
    return dev


def sync_local_to_cloud(retries: int = 2) -> dict:
    """Sinkronisasi DUA ARAH penuh (dipanggil otomatis saat app ditutup).
    Jalur penutupan aplikasi memakai `retries=0` agar aplikasi tidak tertunda
    keluar saat jaringan/DNS sedang bermasalah."""
    return _run_sync(mode="sync", retries=retries)


def pull_from_cloud(mode: str = "auto") -> dict:
    """Tarik data cloud -> lokal. mode "setup" untuk perangkat baru (lokal harus
    kosong), "merge"/"auto" untuk dua arah pada perangkat berisi data.
    SELALU mengembalikan dict — tidak pernah melempar exception."""
    if mode == "auto":
        try:
            local_schema = _build_schema(local_engine, TABLE_ORDER)
            mode = "setup" if not _local_has_data(local_schema) else "sync"
        except Exception:
            mode = "sync"
    return _run_sync(mode=mode)


def maybe_auto_pull() -> None:
    """Dipanggil di thread latar saat aplikasi start (main.py): sinkronisasi dua
    arah — perangkat baru mengunduh seluruh data cloud, perangkat lama menarik
    perubahan perangkat lain & mengirim perubahan lokalnya. Tidak pernah
    melempar exception."""
    try:
        if get_cloud_engine() is None:
            return
        result = _run_sync(mode="auto")
        if result["status"] == "ok":
            print(
                f"[CloudSync] Auto-sync start: insert={result['inserted']} "
                f"update={result['updated']} delete={result['deleted']} "
                f"pull={result['pulled']}"
            )
    except Exception as e:
        print(f"[CloudSync] Auto-sync dilewati: {e}")


def main() -> int:
    """Jalankan sinkronisasi dari baris perintah (python -m utils.cloud_sync).

    Contoh:
      python -m utils.cloud_sync                -> dua arah penuh
      python -m utils.cloud_sync --pull         -> pull (auto setup/merge)
      python -m utils.cloud_sync --pull setup   -> unduh penuh (lokal harus kosong)
      python -m utils.cloud_sync --pull merge   -> dua arah manual
    """
    args = sys.argv[1:]
    if args and args[0] == "--pull":
        mode = args[1] if len(args) > 1 and args[1] in ("setup", "merge") else "auto"
        result = pull_from_cloud(mode=mode)
        print(f"Status : {result['status']} (mode {result['mode']})")
        print(f"Pesan  : {result['message']}")
        print(
            f"Cloud  : insert={result['inserted']} update={result['updated']} "
            f"delete={result['deleted']}"
        )
        print(
            f"Lokal  : pull={result['pulled']} update={result['updated_local']} "
            f"delete={result['deleted_local']}"
        )
        return 0 if result["status"] in ("ok", "skipped") else 1
    result = sync_local_to_cloud()
    print(f"Status : {result['status']}")
    print(f"Pesan  : {result['message']}")
    print(
        f"Cloud  : insert={result['inserted']} update={result['updated']} "
        f"delete={result['deleted']}"
    )
    print(
        f"Lokal  : pull={result['pulled']} update={result['updated_local']} "
        f"delete={result['deleted_local']}"
    )
    return 0 if result["status"] in ("ok", "skipped") else 1


if __name__ == "__main__":
    sys.exit(main())
