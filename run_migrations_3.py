import os
import sys
import pandas as pd
from datetime import datetime

# Add root directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.database import SessionLocal
from data.models import Person, SkuMaster, DebtEntry, DebtPayment

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
        db.flush()
    return person

def get_sku_id(db, kode_sku):
    if pd.isna(kode_sku) or not str(kode_sku).strip():
        return None
    kode_sku = str(kode_sku).strip()
    sku = db.query(SkuMaster).filter(SkuMaster.kode_sku == kode_sku).first()
    return sku.id if sku else None

# --- Migration Functions ---
def migrate_barang_terhutang(db):
    print("\nMigrating Barang Terhutang...")
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='Barang_Terhutang')
        count_debt, count_pay = 0, 0
        
        for _, row in df.iterrows():
            # 1. READ LEFT SIDE (HUTANG)
            tgl_ambil = str(row.get('Tgl Ambil', '')).split()[0]
            nama = row.get('Nama')
            sku_kode = row.get('SKU')
            qty = row.get('Qty')
            total = row.get('Total')
            
            # Skip invalid rows
            if pd.isna(tgl_ambil) or tgl_ambil == 'nan' or pd.isna(total) or str(total).strip() == '': 
                continue
                
            person = get_or_create_person(db, nama, 'SUPPLIER')
            sku_id = get_sku_id(db, sku_kode)
            nominal_hutang = float(total)
            
            if not person: continue

            # Create Debt Entry
            entry = DebtEntry(
                tipe_hutang='BARANG',
                tanggal=tgl_ambil,
                person_id=person.id,
                keterangan=f"Ambil {sku_kode}",
                sku_id=sku_id,
                qty=int(qty) if pd.notna(qty) else None,
                nominal_hutang=nominal_hutang,
                status='OPEN',
                catatan="Migrasi Stage 3 (Excel)"
            )
            db.add(entry)
            db.flush() # Save temporarily to get the entry.id
            count_debt += 1

            # 2. READ RIGHT SIDE (PELUNASAN)
            # Pandas adds '.1' to duplicate column names automatically
            tgl_lunas = str(row.get('Tgl Lunas', '')).split()[0]
            total_lunas = row.get('Total Lunas')

            if pd.notna(total_lunas) and str(total_lunas).strip() != '':
                nominal_bayar = float(total_lunas)
                if nominal_bayar > 0:
                    pay = DebtPayment(
                        debt_entry_id=entry.id,
                        tanggal_bayar=tgl_lunas if tgl_lunas != 'nan' else tgl_ambil,
                        nominal_bayar=nominal_bayar,
                        metode='MIGRASI',
                        catatan="Pelunasan dari Migrasi Stage 3"
                    )
                    db.add(pay)
                    count_pay += 1
                    
                    # Update status
                    if nominal_bayar >= nominal_hutang:
                        entry.status = 'LUNAS'
                    else:
                        entry.status = 'PARTIAL'

        db.commit()
        print(f"  -> Success: {count_debt} Debts and {count_pay} Payments imported.")
    except Exception as e:
        print(f"  -> Error: {e}")
        db.rollback()

def migrate_modal_hutang(db):
    print("\nMigrating Modal Hutang...")
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='Modal_Hutang')
        count_debt, count_pay = 0, 0
        
        for _, row in df.iterrows():
            # 1. READ LEFT SIDE (HUTANG MODAL/BAHAN)
            tanggal = str(row.get('Tanggal', '')).split()[0]
            nama = row.get('Nama')
            jenis = row.get('Jenis')
            kredit = row.get('Kredit')
            
            # Kadang kredit kosong dan diisi di Total
            total_fallback = row.get('Total') 
            nominal_hutang = float(kredit) if pd.notna(kredit) else (float(total_fallback) if pd.notna(total_fallback) else 0)

            if pd.isna(tanggal) or tanggal == 'nan' or nominal_hutang == 0: 
                continue

            person = get_or_create_person(db, nama, 'SUPPLIER')
            if not person: continue

            entry = DebtEntry(
                tipe_hutang='MODAL',
                tanggal=tanggal,
                person_id=person.id,
                keterangan=str(jenis) if pd.notna(jenis) else "Hutang Modal",
                nominal_hutang=nominal_hutang,
                status='OPEN',
                catatan="Migrasi Stage 3 (Excel)"
            )
            db.add(entry)
            db.flush()
            count_debt += 1

            # 2. READ RIGHT SIDE (PELUNASAN / DEPOSIT)
            tgl_lunas = str(row.get('Tanggal.1', '')).split()[0]
            deposit = row.get('Deposit')
            
            if pd.notna(deposit) and str(deposit).strip() != '':
                nominal_bayar = float(deposit)
                if nominal_bayar > 0:
                    pay = DebtPayment(
                        debt_entry_id=entry.id,
                        tanggal_bayar=tgl_lunas if tgl_lunas != 'nan' else tanggal,
                        nominal_bayar=nominal_bayar,
                        metode='MIGRASI'
                    )
                    db.add(pay)
                    count_pay += 1
                    
                    if nominal_bayar >= nominal_hutang:
                        entry.status = 'LUNAS'
                    else:
                        entry.status = 'PARTIAL'

        db.commit()
        print(f"  -> Success: {count_debt} Debts and {count_pay} Payments imported.")
    except Exception as e:
        print(f"  -> Error: {e}")
        db.rollback()

if __name__ == "__main__":
    print("=== ESSA STORE MIGRATION SCRIPT: STAGE 3 (HUTANG PIUTANG) ===")
    db = SessionLocal()
    try:
        migrate_barang_terhutang(db)
        migrate_modal_hutang(db)
        print("\n=== DATA MIGRATION 100% COMPLETE ===")
    finally:
        db.close()