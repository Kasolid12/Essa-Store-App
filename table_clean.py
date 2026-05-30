from data.database import engine
from data.models.base import Base

# --- IMPORT SEMUA MODEL SECARA EKSPLISIT ---
# Ini wajib dilakukan agar SQLAlchemy "membaca" semua rancangan tabel 
# sebelum mengeksekusi perintah pembuatan database.
from data.models import (
    bon, catatan_harian, debt, invoice, 
    master, person, salary, sku, stock_audit
)

def create_missing_tables():
    print("Mendeteksi seluruh model Python dan membangun tabel di essa.db...")
    try:
        # Membuat semua tabel yang belum ada
        Base.metadata.create_all(bind=engine)
        print("✅ Berhasil! Semua tabel baru (termasuk Invoice, Stock Audit, dan Pengsup) sudah dibuat.")
    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")

if __name__ == '__main__':
    create_missing_tables()