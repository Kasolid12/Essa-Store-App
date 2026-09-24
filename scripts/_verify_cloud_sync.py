"""Verifikasi: count lokal vs cloud (dipakai setelah regresi sync dua arah)."""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402
from data.database import get_cloud_engine  # noqa: E402

c = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "essa.db"))
local = {}
for t in ["sku_master", "persons", "invoices", "app_settings", "clients",
          "invoice_lines", "client_receivables", "debt_entries"]:
    local[t] = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
c.close()

ok = True
with get_cloud_engine().connect() as cc:
    for t in local:
        n = cc.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
        match = local[t] == n
        ok = ok and match
        print(f"{t:22s} lokal={local[t]:6d} cloud={n:6d}  {'OK' if match else 'BEDA!'}")
print("\nSEMUA COCOK" if ok else "\nADA PERBEDAAN!")
