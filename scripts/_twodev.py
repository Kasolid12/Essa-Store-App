"""Helper langkah-langkah uji dua perangkat (dipanggil via subprocess oleh
scripts/_test_twoway.py). Setiap langkah berjalan di PROSES TERPISAH dengan
APP_DATABASE_URL / CLOUD_DATABASE_URL berbeda — simulasi 2 perangkat + cloud.

Cloud tiruan = file SQLite (bukan Neon) agar uji tidak menyentuh data produksi.
Semua logika sync (ID mapping, LWW, tombstone) tetap teruji karena dialektik
umum SQLAlchemy; bagian khusus Postgres (sequence) hanya diuji lewat max+1.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _db():
    sys.path.insert(0, ROOT)
    from data.database import engine as le, get_cloud_engine, SessionLocal
    from data.models.base import Base
    import data.models  # noqa: F401
    return le, get_cloud_engine(), SessionLocal, Base


def _create_schema():
    le, ce, _, Base = _db()
    Base.metadata.create_all(bind=le)
    Base.metadata.create_all(bind=ce)


def _sync_and_report(tag):
    from utils.cloud_sync import sync_local_to_cloud
    r1 = sync_local_to_cloud()
    r2 = sync_local_to_cloud()  # run kedua harus konvergen (0 perubahan)
    print(f"[{tag}] run1: insert={r1['inserted']} update={r1['updated']} "
          f"delete={r1['deleted']} pull={r1['pulled']} lu={r1['updated_local']} "
          f"ld={r1['deleted_local']} status={r1['status']}")
    print(f"[{tag}] run2 (idempoten): insert={r2['inserted']} update={r2['updated']} "
          f"delete={r2['deleted']} pull={r2['pulled']} lu={r2['updated_local']} "
          f"ld={r2['deleted_local']}")
    assert r1["status"] == "ok", f"sync gagal: {r1}"
    zero = ("inserted", "updated", "deleted", "pulled", "updated_local", "deleted_local")
    assert all(r2[k] == 0 for k in zero), f"TIDAK KONVERGEN: {r2}"
    return r1


# ── Langkah 1: Perangkat A membuat data & sync perdana ──
def step_seed_a():
    _create_schema()
    le, ce, SessionLocal, _ = _db()
    # Identitas perangkat DETERMINISTIK (Fase 6.3) agar kepemilikan bisa diuji.
    # CURRENT_DEVICE_ID membuat tulis ORM mengisi created_by_device otomatis.
    import data.models.base as _base
    _base.CURRENT_DEVICE_ID = "DEVA"
    from sqlalchemy import text
    with le.begin() as c:
        c.execute(text(
            "INSERT INTO app_settings (key, value, updated_at) "
            "VALUES ('device_id', 'DEVA', '2026-08-01 09:00:00')"))
    from data.models.person import Person
    from data.models.sku import SkuMaster
    from data.models.invoice import Invoice, InvoiceLine
    db = SessionLocal()
    db.add_all([
        Person(id=1, nama="Andi", person_type="KLIEN"),
        Person(id=2, nama="Budi", person_type="KLIEN"),
        SkuMaster(id=1, kode_sku="SKU-A", nama_produk="Produk A"),
        SkuMaster(id=2, kode_sku="SKU-B", nama_produk="Produk B"),
        Invoice(id=1, nomor_invoice="INV-001", tanggal="2026-08-01", person_id=1),
        Invoice(id=2, nomor_invoice="INV-002", tanggal="2026-08-02", person_id=2),
        InvoiceLine(id=1, invoice_id=1, sku_id=1, qty=2, harga_satuan=100, diskon_line=0, subtotal=200),
        InvoiceLine(id=2, invoice_id=1, sku_id=2, qty=1, harga_satuan=50, diskon_line=0, subtotal=50),
        InvoiceLine(id=3, invoice_id=2, sku_id=1, qty=1, harga_satuan=100, diskon_line=0, subtotal=100),
    ])
    db.commit()
    db.close()
    _sync_and_report("A")
    print("[A] seeded & synced")


# ── Langkah 2: Perangkat B membuat data STANDALONE (id tumpang tindih) ──
def step_seed_b():
    _create_schema()
    le, ce, SessionLocal, _ = _db()
    import data.models.base as _base
    _base.CURRENT_DEVICE_ID = "DEVB"
    from sqlalchemy import text
    ts = "2026-08-01 09:00:00.000000"  # updated_at NON-NULL kedua sisi -> tabrakan (bukan edit)
    with le.begin() as c:
        c.execute(text(
            "INSERT INTO app_settings (key, value, updated_at) "
            "VALUES ('device_id', 'DEVB', '2026-08-01 09:00:00')"))
        c.execute(text(
            "INSERT INTO persons (id, nama, person_type, is_active, is_deleted, created_at, updated_at, created_by_device) "
            f"VALUES (1,'Orang B','KLIEN',1,0,'2026-08-01 09:00:00', '{ts}', 'DEVB')"))
        c.execute(text(
            "INSERT INTO persons (id, nama, person_type, is_active, is_deleted, created_at, updated_at, created_by_device) "
            f"VALUES (3,'Citra','KLIEN',1,0,'2026-08-01 09:00:00', '{ts}', 'DEVB')"))
        c.execute(text(
            "INSERT INTO sku_master (id, kode_sku, nama_produk, harga_jual, harga_modal, kain_cost, potongan_cost, is_active, is_deleted, created_at, updated_at, created_by_device) "
            f"VALUES (1,'SKU-BX','Produk BX',0,0,0,0,1,0,'2026-08-01 09:00:00', '{ts}', 'DEVB')"))
        c.execute(text(
            "INSERT INTO sku_master (id, kode_sku, nama_produk, harga_jual, harga_modal, kain_cost, potongan_cost, is_active, is_deleted, created_at, updated_at, created_by_device) "
            f"VALUES (3,'SKU-C','Produk C',0,0,0,0,1,0,'2026-08-01 09:00:00', '{ts}', 'DEVB')"))
        c.execute(text(
            "INSERT INTO invoices (id, nomor_invoice, tanggal, person_id, subtotal, diskon, ongkir, total, dp, sisa, status, is_deleted, created_at, updated_at, created_by_device) "
            f"VALUES (1,'INV-B1','2026-08-01',1,0,0,0,0,0,0,'OPEN',0,'2026-08-01 09:00:00', '{ts}', 'DEVB')"))
        c.execute(text(
            "INSERT INTO invoices (id, nomor_invoice, tanggal, person_id, subtotal, diskon, ongkir, total, dp, sisa, status, is_deleted, created_at, updated_at, created_by_device) "
            f"VALUES (3,'INV-B2','2026-08-01',3,0,0,0,0,0,0,'OPEN',0,'2026-08-01 09:00:00', '{ts}', 'DEVB')"))
        c.execute(text(
            "INSERT INTO invoice_lines (id, invoice_id, sku_id, qty, harga_satuan, diskon_line, subtotal, updated_at, created_by_device) "
            f"VALUES (1,1,1,1,75,0,75, '{ts}', 'DEVB')"))
        c.execute(text(
            "INSERT INTO invoice_lines (id, invoice_id, sku_id, qty, harga_satuan, diskon_line, subtotal, updated_at, created_by_device) "
            f"VALUES (4,3,3,1,80,0,80, '{ts}', 'DEVB')"))
    print("[B] standalone seeded (id 1 tabrakan dengan A, id 3 baru)")


# ── Langkah 3 & 4 & 9: sync dua arah (dipakai oleh A dan B) ──
def step_sync():
    return _sync_and_report("SYNC")


# ── Langkah 5: A mengedit person 1 via ORM (updated_at & updated_by_device otomatis) ──
def step_lww_a():
    le, ce, SessionLocal, _ = _db()
    import data.models.base as _base
    _base.CURRENT_DEVICE_ID = "DEVA"
    from sqlalchemy import text
    from data.models.person import Person
    db = SessionLocal()
    p = db.query(Person).filter(Person.id == 1).one()
    p.nama = "Andi A"
    db.commit()
    db.close()
    r = _sync_and_report("A(LWW)")
    assert r["updated"] == 1, "cloud person 1 harus ter-update (Andi A)"
    with le.connect() as c:
        ub = c.execute(text("SELECT updated_by_device FROM persons WHERE id=1")).scalar()
    assert ub == "DEVA", f"updated_by_device harus DEVA (event ORM), dapat: {ub}"
    print("[A] person 1 -> 'Andi A' (edit ORM, updated_by_device=DEVA otomatis) pushed")


# ── Langkah 6: B mengedit Andi lokalnya via ORM (lebih baru) ──
def step_lww_b():
    le, ce, SessionLocal, _ = _db()
    import data.models.base as _base
    _base.CURRENT_DEVICE_ID = "DEVB"
    from sqlalchemy import text
    from data.models.person import Person
    with le.connect() as c:
        nm = c.execute(text("SELECT nama FROM persons WHERE id=4")).scalar()
    assert nm == "Andi", f"B local id 4 harus 'Andi', dapat: {nm}"
    db = SessionLocal()
    p = db.query(Person).filter(Person.id == 4).one()
    p.nama = "Andi B"
    db.commit()
    db.close()
    r = _sync_and_report("B(LWW)")
    assert r["updated"] == 1, "cloud person 1 harus ter-update (Andi B)"
    with le.connect() as c:
        ub = c.execute(text("SELECT updated_by_device FROM persons WHERE id=4")).scalar()
    assert ub == "DEVB", f"updated_by_device harus DEVB (event ORM), dapat: {ub}"
    print("[B] person lokal id 4 ('Andi') -> 'Andi B' (edit ORM, updated_by_device=DEVB otomatis) pushed")


# ── Langkah 7: A sync lagi -> harus MENARIK 'Andi B' dari cloud ──
def step_lww_check():
    le, ce, SessionLocal, _ = _db()
    from sqlalchemy import text
    r = _sync_and_report("A(cek-LWW)")
    with le.connect() as c:
        nm = c.execute(text("SELECT nama FROM persons WHERE id=1")).scalar()
    assert r["updated_local"] >= 1, "A harus menarik versi cloud yang lebih baru"
    assert nm == "Andi B", f"A person 1 harus 'Andi B', dapat: {nm}"
    print(f"[A] LWW OK: person 1 sekarang '{nm}' (cloud menang)")


# ── Langkah 7.5: A mengedit baris REMAP milik B (Orang B, lokal 3 -> cloud 3) ──
def step_edit_b_row_a():
    le, ce, SessionLocal, _ = _db()
    from sqlalchemy import text
    from datetime import datetime, timedelta
    ts = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f")
    with le.begin() as c:
        c.execute(text(
            "UPDATE persons SET nama='Orang B Edit A', updated_at=:ts WHERE id=3"),
            {"ts": ts})
    r = _sync_and_report("A(edit-B-row)")
    assert r["updated"] == 1, "cloud person 3 harus ter-update"
    print(f"[A] Orang B (lokal id 3) -> 'Orang B Edit A' @{ts} pushed")


# ── Langkah 7.6: B sync -> MENARIK edit itu ke id lokalnya SENDIRI (1) ──
def step_pull_remapped():
    le, ce, SessionLocal, _ = _db()
    from sqlalchemy import text
    r = _sync_and_report("B(pull-remap)")
    with le.connect() as c:
        nm = c.execute(text("SELECT nama FROM persons WHERE id=1")).scalar()
        n = c.execute(text("SELECT COUNT(*) FROM persons")).fetchone()[0]
    assert r["updated_local"] == 1, "B harus menarik 'Orang B Edit A'"
    assert nm == "Orang B Edit A", f"B person 1 harus 'Orang B Edit A', dapat: {nm}"
    assert n == 4, f"B tidak boleh punya duplikat (count={n})"
    print(f"[B] pull baris remap OK: person 1 = '{nm}' (tanpa duplikat)")


# ── Langkah 7.7: A menghapus Orang B (person 3) -> cloud ikut terhapus ──
def step_del_remapped():
    le, ce, SessionLocal, _ = _db()
    from sqlalchemy import text
    with le.begin() as c:
        c.execute(text("DELETE FROM persons WHERE id=3"))
    r = _sync_and_report("A(del-remap)")
    assert r["deleted"] == 1, "cloud person 3 harus terhapus"
    print("[A] Orang B dihapus lokal, cloud ikut terhapus")


# ── Langkah 7.8: B mengedit Orang B lokal (id 1) setelah cloud menghapusnya ──
#    Edit lokal LEBIH BARU -> baris di-cloud "dihidupkan kembali" di id yang sama
def step_resurrect():
    le, ce, SessionLocal, _ = _db()
    from sqlalchemy import text
    from datetime import datetime, timedelta
    ts = (datetime.now() + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S.%f")
    with le.begin() as c:
        c.execute(text(
            "UPDATE persons SET nama='Orang B Edit B', updated_at=:ts WHERE id=1"),
            {"ts": ts})
    r = _sync_and_report("B(resurrect)")
    assert r["inserted"] == 1, "cloud person 3 harus dihidupkan kembali (insert 1)"
    print("[B] Orang B diedit (edit lokal paling baru) -> cloud dihidupkan kembali di id yang sama")


# ── Langkah 7.9: A sync -> menarik 'Orang B Edit B' dari cloud id 3 ──
def step_verify_resurrect():
    le, ce, SessionLocal, _ = _db()
    from sqlalchemy import text
    r = _sync_and_report("A(verify-resurrect)")
    with le.connect() as c:
        nm = c.execute(text("SELECT nama FROM persons WHERE id=3")).scalar()
    assert nm == "Orang B Edit B", f"A person 3 harus 'Orang B Edit B', dapat: {nm}"
    print(f"[A] resurrect OK: person 3 = '{nm}' (cloud id sama)")


# ── Langkah 15 (Fase 6.3): A membuat person 100 'Identik' + 101 'Copy Lama' (DEVA) ──
def step_owner_a():
    le, ce, SessionLocal, _ = _db()
    from sqlalchemy import text
    with le.begin() as c:
        c.execute(text(
            "INSERT INTO persons (id, nama, person_type, is_active, is_deleted, created_at, updated_at, created_by_device) "
            "VALUES (100,'Identik','KLIEN',1,0,'2026-08-01 08:00:00','2026-08-01 08:00:00.000000','DEVA')"))
        c.execute(text(
            "INSERT INTO persons (id, nama, person_type, is_active, is_deleted, created_at, updated_at, created_by_device) "
            "VALUES (101,'Copy Lama','KLIEN',1,0,'2026-08-01 08:00:00','2026-08-01 08:00:00.000000','DEVA')"))
    r = _sync_and_report("A(owner)")
    assert r["inserted"] == 2, "cloud harus menerima person 100 & 101"
    print("[A] person 100 'Identik' & 101 'Copy Lama' (owner DEVA) pushed")


# ── Langkah 16 (Fase 6.3): B membuat KONTEN IDENTIK di id yang sama ──
#    person 100 'Identik' (owner DEVB) -> baris BERBEDA -> tabrakan -> id cloud baru
#    person 101 'Copy Lama' (owner NULL, salinan DB lama) -> baris SAMA -> identity
def step_owner_b():
    le, ce, SessionLocal, _ = _db()
    from sqlalchemy import text
    with le.begin() as c:
        c.execute(text(
            "INSERT INTO persons (id, nama, person_type, is_active, is_deleted, created_at, updated_at, created_by_device) "
            "VALUES (100,'Identik','KLIEN',1,0,'2026-08-01 08:00:00','2026-08-01 08:00:00.000000','DEVB')"))
        c.execute(text(
            "INSERT INTO persons (id, nama, person_type, is_active, is_deleted, created_at, updated_at) "
            "VALUES (101,'Copy Lama','KLIEN',1,0,'2026-08-01 08:00:00','2026-08-01 08:00:00.000000')"))
    r = _sync_and_report("B(owner)")
    assert r["inserted"] == 1, f"Identik B harus di-remap (insert cloud 1), dapat {r['inserted']}"
    with le.connect() as c:
        m100 = c.execute(text(
            "SELECT cloud_id FROM sync_id_map WHERE table_name='persons' AND local_id=100")).scalar()
        m101 = c.execute(text(
            "SELECT cloud_id FROM sync_id_map WHERE table_name='persons' AND local_id=101")).scalar()
        cnt = c.execute(text("SELECT COUNT(*) FROM persons WHERE nama='Identik'")).fetchone()[0]
        cl = c.execute(text("SELECT COUNT(*) FROM persons WHERE nama='Copy Lama'")).fetchone()[0]
    assert m100 != 100, f"Identik lokal 100 harus DIREMAP (dapat {m100})"
    assert m101 == 101, f"Copy Lama lokal 101 harus IDENTITY ke cloud 101 (dapat {m101})"
    assert cnt == 2, f"B harus punya 2 'Identik' (miliknya + tarikan A), dapat {cnt}"
    assert cl == 1, f"'Copy Lama' di B harus tetap 1 (salinan lama digabung, bukan diduplikasi), dapat {cl}"
    print(f"[B] Identik 100 -> cloud {m100} (tabrakan kepemilikan) | Copy Lama 101 -> cloud {m101} "
          f"(identity salinan lama) | Identik lokal: {cnt}, Copy Lama lokal: {cl}")


# ── Langkah 17 (Fase 6.3): A sync -> menarik 'Identik' milik B tanpa duplikat ──
def step_owner_check():
    le, ce, SessionLocal, _ = _db()
    from sqlalchemy import text
    r = _sync_and_report("A(owner-check)")
    with le.connect() as c:
        cnt = c.execute(text("SELECT COUNT(*) FROM persons WHERE nama='Identik'")).fetchone()[0]
        cl = c.execute(text("SELECT COUNT(*) FROM persons WHERE nama='Copy Lama'")).fetchone()[0]
    assert r["pulled"] >= 1, "A harus menarik Identik milik B dari cloud"
    assert cnt == 2, f"A harus punya 2 'Identik', dapat {cnt}"
    assert cl == 1, f"A 'Copy Lama' harus tetap 1, dapat {cl}"
    print(f"[A] Identik: {cnt}, Copy Lama: {cl} (tarikan cloud OK, tanpa duplikat)")


# ── Langkah 8: A menghapus invoice 3 (INV-B1 milik B) + line 4, lalu sync ──
def step_del_a():
    le, ce, SessionLocal, _ = _db()
    from sqlalchemy import text
    with le.connect() as c:
        n = c.execute(text("SELECT nomor_invoice FROM invoices WHERE id=3")).scalar()
    assert n == "INV-B1", f"A local invoice 3 harus INV-B1, dapat: {n}"
    with le.begin() as c:
        c.execute(text("DELETE FROM invoice_lines WHERE id=4"))
        c.execute(text("DELETE FROM invoices WHERE id=3"))
    r = _sync_and_report("A(del)")
    assert r["deleted"] >= 2, "Cloud harus ikut menghapus invoice + line"
    print("[A] INV-B1 + line dihapus lokal, cloud ikut terhapus")


# ── Langkah 10: pemeriksaan akhir (baca file langsung, tanpa engine) ──
def step_final():
    import sqlite3
    a = sqlite3.connect(os.path.join(ROOT, "twoway_a.db"))
    b = sqlite3.connect(os.path.join(ROOT, "twoway_b.db"))
    c = sqlite3.connect(os.path.join(ROOT, "twoway_cloud.db"))

    def q(conn, sql):
        return conn.execute(sql).fetchall()

    print("\n=== CLOUD (final) ===")
    print(" persons :", q(c, "SELECT id, nama FROM persons ORDER BY id"))
    print(" invoices:", q(c, "SELECT id, nomor_invoice, person_id FROM invoices ORDER BY id"))
    print(" lines   :", q(c, "SELECT id, invoice_id, sku_id FROM invoice_lines ORDER BY id"))
    print(" sku     :", q(c, "SELECT id, kode_sku FROM sku_master ORDER BY id"))

    assert q(c, "SELECT nama FROM persons WHERE id=1") == [("Andi B",)], "LWW person 1"
    assert q(c, "SELECT nama FROM persons WHERE id=3") == [("Orang B Edit B",)], "resurrect di id sama"
    assert q(c, "SELECT COUNT(*) FROM invoices WHERE nomor_invoice='INV-B1'") == [(0,)], "INV-B1 harus terhapus di cloud"
    assert q(c, "SELECT COUNT(*) FROM invoices WHERE nomor_invoice='INV-B2'") == [(1,)], "INV-B2 harus bertahan"
    fk_viol = q(c, "PRAGMA foreign_key_check")
    assert not fk_viol, f"FK VIOLATION di cloud: {fk_viol}"

    print("\n=== DEVICE A ===")
    assert q(a, "SELECT nama FROM persons WHERE id=1") == [("Andi B",)], "A person 1"
    assert q(a, "SELECT COUNT(*) FROM invoices WHERE nomor_invoice='INV-B1'") == [(0,)], "A tidak punya INV-B1"
    assert q(a, "SELECT COUNT(*) FROM invoices WHERE nomor_invoice='INV-B2'") == [(1,)], "A punya INV-B2"
    print(" persons :", q(a, "SELECT id, nama FROM persons ORDER BY id"))
    print(" invoices:", q(a, "SELECT id, nomor_invoice FROM invoices ORDER BY id"))

    print("\n=== DEVICE B ===")
    assert q(b, "SELECT nama FROM persons WHERE id=1") == [("Orang B Edit B",)], "B person 1 ikut edit+resurrect"
    assert q(b, "SELECT COUNT(*) FROM persons WHERE nama='Orang B Edit B'") == [(1,)], "B tidak duplikat"
    assert q(b, "SELECT COUNT(*) FROM invoices WHERE nomor_invoice='INV-B1'") == [(0,)], "B INV-B1 ikut terhapus"
    assert q(b, "SELECT COUNT(*) FROM invoices WHERE nomor_invoice='INV-B2'") == [(1,)], "B punya INV-B2"
    print(" persons :", q(b, "SELECT id, nama FROM persons ORDER BY id"))
    print(" invoices:", q(b, "SELECT id, nomor_invoice FROM invoices ORDER BY id"))

    # Pemetaan id: B's Orang B (lokal 1) harus -> cloud 3
    m = q(b, "SELECT local_id, cloud_id FROM sync_id_map WHERE table_name='persons' AND local_id=1")
    assert m and m[0][1] == 3, f"map B persons 1 -> cloud {m}"
    print("\n map B persons 1 -> cloud:", m)

    print("\n=== FASE 6.3: KEPEMILIKAN PERANGKAT ===")
    # 'Identik': dua perangkat membuat konten SAMA di id sama -> harus TETAP 2 baris
    assert q(c, "SELECT COUNT(*) FROM persons WHERE nama='Identik'") == [(2,)], "cloud harus punya 2 Identik"
    assert q(a, "SELECT COUNT(*) FROM persons WHERE nama='Identik'") == [(2,)], "A punya 2 Identik"
    assert q(b, "SELECT COUNT(*) FROM persons WHERE nama='Identik'") == [(2,)], "B punya 2 Identik"
    # 'Copy Lama': salinan DB lama (owner NULL) konten identik -> digabung, bukan duplikat
    assert q(c, "SELECT COUNT(*) FROM persons WHERE nama='Copy Lama'") == [(1,)], "Copy Lama tidak diduplikasi"
    assert q(a, "SELECT COUNT(*) FROM persons WHERE nama='Copy Lama'") == [(1,)], "A Copy Lama = 1"
    assert q(b, "SELECT COUNT(*) FROM persons WHERE nama='Copy Lama'") == [(1,)], "B Copy Lama = 1"
    # Pemilik tercatat di cloud: satu baris DEVA, satu baris DEVB
    owners = [r[0] for r in q(c, "SELECT created_by_device FROM persons WHERE nama='Identik' ORDER BY id")]
    assert "DEVA" in owners and "DEVB" in owners, f"owner cloud salah: {owners}"
    print(" owners Identik di cloud:", owners)
    # created_by_device terisi OTOMATIS saat INSERT via ORM (bukan hanya raw SQL)
    assert q(c, "SELECT created_by_device FROM persons WHERE id=1") == [("DEVA",)], \
        "person 1 dibuat via ORM -> owner harus DEVA"
    # updated_by_device mencatat perangkat yang terakhir EDIT (LWW dimenangkan B)
    assert q(c, "SELECT updated_by_device FROM persons WHERE id=1") == [("DEVB",)], \
        "person 1 diedit terakhir oleh B -> updated_by_device harus DEVB"
    print("\n=== SEMUA ASERSI LULUS ===")
