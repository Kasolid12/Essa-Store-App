import os
import sys
import pandas as pd
from datetime import datetime

# Add root directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.database import SessionLocal
from data.models import (
    Person, SkuMaster, HasilCutting, DistribusiCutting, 
    ModalOperasional, PengeluaranOffline
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, 'Pencatatan Harian.xlsx')

# --- Helper Functions ---
def get_or_create_person(db, nama, default_type='LAINNYA'):
    if pd.isna(nama) or not str(nama).strip():
        return None
    nama = str(nama).strip()
    person = db.query(Person).filter(Person.nama_uppercase == nama.upper()).first()
    if not person:
        person = Person(nama=nama, person_type=default_type)
        db.add(person)
        db.flush() # Get ID immediately
    return person

def get_sku_id(db, kode_sku):
    if pd.isna(kode_sku) or not str(kode_sku).strip():
        return None
    kode_sku = str(kode_sku).strip()
    sku = db.query(SkuMaster).filter(SkuMaster.kode_sku == kode_sku).first()
    
    # FIX: If the SKU is missing (like 'DG-M' or 'Kertas Resi'), auto-create it!
    if not sku:
        sku = SkuMaster(
            kode_sku=kode_sku, 
            nama_produk=f"{kode_sku} (Auto-Migrasi Offline)", 
            harga_modal=0.0,
            kategori="OFFLINE/INDUK"
        )
        db.add(sku)
        db.flush() # Get the new ID immediately
        
    return sku.id

# --- Migration Functions ---
def migrate_hasil_cutting(db):
    print("\nMigrating Hasil Cutting...")
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='Hasil_Cutting')
        count, skipped = 0, 0
        
        for _, row in df.iterrows():
            tanggal = str(row.get('Tanggal', '')).split()[0] # Ambil YYYY-MM-DD
            sku_kode = row.get('SKU')
            qty = row.get('Jumlah')
            
            if pd.isna(tanggal) or pd.isna(qty): continue
            
            sku_id = get_sku_id(db, sku_kode)
            if not sku_id:
                skipped += 1
                continue
                
            hc = HasilCutting(tanggal=tanggal, sku_id=sku_id, qty=int(qty), catatan="Migrasi Stage 2")
            db.add(hc)
            count += 1
            
        db.commit()
        print(f"  -> Success: {count} records imported. (Skipped {skipped} unknown SKUs)")
    except Exception as e:
        print(f"  -> Error: {e}")
        db.rollback()

def migrate_distribusi_cutting(db):
    print("\nMigrating Distribusi Cutting...")
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='Distribusi_Cutting')
        count, skipped = 0, 0
        
        for _, row in df.iterrows():
            tanggal = str(row.get('Tanggal', '')).split()[0]
            jenis = str(row.get('Jenis', '')).strip().upper()
            nama = row.get('Nama')
            sku_kode = row.get('SKU')
            qty = row.get('Jumlah')
            
            if pd.isna(tanggal) or pd.isna(qty): continue
            
            person = get_or_create_person(db, nama, 'PENJAHIT' if 'JAHIT' in jenis else 'PENGSUP')
            sku_id = get_sku_id(db, sku_kode)
            
            if not sku_id or not person:
                skipped += 1
                continue
                
            dc = DistribusiCutting(
                tanggal=tanggal, person_id=person.id, jenis=jenis, 
                sku_id=sku_id, qty=int(qty), catatan="Migrasi Stage 2"
            )
            db.add(dc)
            count += 1
            
        db.commit()
        print(f"  -> Success: {count} records imported. (Skipped {skipped} due to missing SKU/Person)")
    except Exception as e:
        print(f"  -> Error: {e}")
        db.rollback()

def migrate_pengeluaran_offline(db):
    print("\nMigrating Pengeluaran Offline...")
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='Pengeluaran_Barang_Offline')
        count = 0
        
        for _, row in df.iterrows():
            tanggal = str(row.get('Tanggal', '')).split()[0]
            nama = row.get('Nama')
            sku_kode = row.get('SKU')
            qty = row.get('Jumlah')
            
            # Handle empty values safely
            if pd.isna(tanggal) or pd.isna(qty): continue
            
            # Parse harga and total, defaulting to 0 if empty
            harga = float(row.get('Harga Satuan')) if pd.notna(row.get('Harga Satuan')) else 0.0
            total = float(row.get('Total')) if pd.notna(row.get('Total')) else (int(qty) * harga)
            
            person = get_or_create_person(db, nama, 'KLIEN')
            sku_id = get_sku_id(db, sku_kode)
            
            if not sku_id: continue # Wajib ada SKU
                
            po = PengeluaranOffline(
                tanggal=tanggal, sku_id=sku_id, qty=int(qty), 
                harga_satuan=harga, total=total, 
                person_id=person.id if person else None,
                catatan="Migrasi Stage 2"
            )
            db.add(po)
            count += 1
            
        db.commit()
        print(f"  -> Success: {count} records imported.")
    except Exception as e:
        print(f"  -> Error: {e}")
        db.rollback()

def migrate_modal_operasional(db):
    print("\nMigrating Modal Operasional...")
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='Modal_Operasional')
        count = 0
        
        for _, row in df.iterrows():
            tanggal = str(row.get('Tanggal', '')).split()[0]
            jenis = str(row.get('Jenis', '')).strip().upper()
            keterangan = str(row.get('Nama', '')).strip()
            
            if pd.isna(tanggal) or not keterangan or keterangan == 'nan': continue
            
            # In Excel, total might be blank if it's just Qty * Harga
            qty = float(row.get('Jumlah')) if pd.notna(row.get('Jumlah')) else 1.0
            harga = float(row.get('Harga Satuan')) if pd.notna(row.get('Harga Satuan')) else 0.0
            
            total_val = row.get('Total')
            if pd.notna(total_val) and str(total_val).strip() != '':
                nominal = float(total_val)
            else:
                nominal = qty * harga
            
            if nominal == 0: continue
                
            mo = ModalOperasional(
                tanggal=tanggal, jenis=jenis, keterangan=keterangan, 
                nominal=nominal, catatan="Migrasi Stage 2"
            )
            db.add(mo)
            count += 1
            
        db.commit()
        print(f"  -> Success: {count} records imported.")
    except Exception as e:
        print(f"  -> Error: {e}")
        db.rollback()

if __name__ == "__main__":
    print("=== ESSA STORE MIGRATION SCRIPT: STAGE 2 ===")
    db = SessionLocal()
    try:
        migrate_hasil_cutting(db)
        migrate_distribusi_cutting(db)
        migrate_pengeluaran_offline(db)
        migrate_modal_operasional(db)
        print("\n=== STAGE 2 COMPLETE ===")
    finally:
        db.close()