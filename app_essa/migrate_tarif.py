# migrate_tarif.py
from data.database import engine, SessionLocal
from data.models.base import Base  # <--- THE FIX: Importing Base from the correct file
from data.models.salary import MasterTarifPenjahit

# 1. Buat tabel baru di database SQLite
Base.metadata.create_all(bind=engine)

# 2. Data lama kamu
HARGA_REF = {
    "JSO": 700, "DG": 900, "DG-L": 1000, "SA-M": 700, "SA-L": 800,
    "SA-XL": 900, "OBRES": 100, "HMD-S": 700, "HMD-M": 800,
    "HMD-L": 900, "Jiso-Adila": 600, "P-Polos": 700,
    "S3": 800, "JSO-Inner": 1000, "Cap": 100,
}

db = SessionLocal()
try:
    # 3. Masukkan ke database jika belum ada
    for kode, harga in HARGA_REF.items():
        exists = db.query(MasterTarifPenjahit).filter(MasterTarifPenjahit.kode_garapan == kode).first()
        if not exists:
            tarif = MasterTarifPenjahit(kode_garapan=kode, harga=float(harga))
            db.add(tarif)
    
    db.commit()
    print("Migrasi Sukses! 19 Tarif Penjahit berhasil dipindahkan ke Database.")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()