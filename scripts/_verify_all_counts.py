"""Bandingkan jumlah baris LOKAL vs CLOUD untuk semua tabel yang disinkronkan."""
import sys
sys.path.insert(0, ".")

import sqlite3
from sqlalchemy import text
from data.database import get_cloud_engine
from utils.sync_tables import TABLE_ORDER

c = sqlite3.connect("essa.db")
e = get_cloud_engine()
bad = 0
with e.connect() as cc:
    for t in TABLE_ORDER:
        lc_n = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        cc_n = cc.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
        mark = "OK" if lc_n == cc_n else "BEDA!"
        if lc_n != cc_n:
            bad += 1
        print(f"{t:32s} lokal={lc_n:6d} cloud={cc_n:6d} {mark}")
c.close()
print("\nRESULT:", "SEMUA COCOK" if bad == 0 else f"{bad} tabel BEDA")
sys.exit(1 if bad else 0)
