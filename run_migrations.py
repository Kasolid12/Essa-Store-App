import os
import sys
import json
import pandas as pd
from datetime import datetime

from alembic.config import Config
from alembic import command

# Add root directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.database import SessionLocal
from data.models import (
    Person, SkuMaster, AppSetting, 
    BonBalance, BonMovement, ClientReceivable
)

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def migrate_settings(db):
    print("Migrating Settings...")
    try:
        with open(os.path.join(BASE_DIR, 'data_hutang_klien.json'), 'r') as f:
            data = json.load(f)
            last_invoice = str(data.get('_last_invoice_no', 0))
            
            setting = AppSetting(key='last_invoice_no', value=last_invoice)
            db.merge(setting)
            db.commit()
            print(f"  -> Settings migrated. Last invoice: {last_invoice}")
    except FileNotFoundError:
        print("  -> data_hutang_klien.json not found, skipping settings.")

def migrate_persons_and_balances(db):
    print("\nMigrating Persons & Balances...")
    
    # 1. Penjahit
    try:
        with open(os.path.join(BASE_DIR, 'database_bon_penjahit.json'), 'r') as f:
            penjahit_data = json.load(f)
            for nama, saldo in penjahit_data.items():
                p = Person(nama=nama.strip(), person_type='PENJAHIT')
                db.add(p)
                db.flush() # Get ID
                if saldo > 0:
                    b = BonBalance(person_id=p.id, saldo=saldo)
                    bm = BonMovement(person_id=p.id, tanggal=datetime.now().strftime("%Y-%m-%d"), 
                                     tipe='TAMBAH', nominal=saldo, sumber='MIGRASI_AWAL', catatan='Saldo awal JSON')
                    db.add_all([b, bm])
    except FileNotFoundError: pass

    # 2. Karyawan
    try:
        with open(os.path.join(BASE_DIR, 'database_bon_karyawan.json'), 'r') as f:
            karyawan_data = json.load(f)
            for nama, saldo in karyawan_data.items():
                if nama.upper() in ['ADMIN', 'DEPT', 'UNKNOWN']: continue # Skip system tags
                p = Person(nama=nama.strip(), person_type='KARYAWAN')
                db.add(p)
                db.flush()
                if saldo > 0:
                    b = BonBalance(person_id=p.id, saldo=saldo)
                    bm = BonMovement(person_id=p.id, tanggal=datetime.now().strftime("%Y-%m-%d"), 
                                     tipe='TAMBAH', nominal=saldo, sumber='MIGRASI_AWAL', catatan='Saldo awal JSON')
                    db.add_all([b, bm])
    except FileNotFoundError: pass

    # 3. Klien (Piutang)
    try:
        with open(os.path.join(BASE_DIR, 'data_hutang_klien.json'), 'r') as f:
            klien_data = json.load(f)
            for nama, saldo in klien_data.items():
                if nama.startswith('_') or nama == 'pelunasan': continue
                p = Person(nama=nama.strip(), person_type='KLIEN')
                db.add(p)
                db.flush()
                if saldo > 0:
                    cr = ClientReceivable(person_id=p.id, nominal=saldo, sisa=saldo, status='OPEN')
                    db.add(cr)
    except FileNotFoundError: pass

    # 4. Lainnya (Kak Hari, Kak Yudi, dll dari data_bon)
    try:
        with open(os.path.join(BASE_DIR, 'data_bon.json'), 'r') as f:
            lainnya_data = json.load(f)
            for nama, saldo in lainnya_data.items():
                p = Person(nama=nama.strip(), person_type='LAINNYA')
                db.add(p)
                db.flush()
                if saldo > 0:
                    b = BonBalance(person_id=p.id, saldo=saldo)
                    bm = BonMovement(person_id=p.id, tanggal=datetime.now().strftime("%Y-%m-%d"), 
                                     tipe='TAMBAH', nominal=saldo, sumber='MIGRASI_AWAL', catatan='Saldo awal JSON')
                    db.add_all([b, bm])
    except FileNotFoundError: pass

    db.commit()
    print("  -> Persons and financial balances migrated successfully.")

def migrate_skus(db):
    print("\nMigrating Master SKUs...")
    try:
        df = pd.read_excel(os.path.join(BASE_DIR, 'MasterSKU.xlsx'), sheet_name=0)
        
        # Clean column names to handle potential trailing spaces in Excel
        df.columns = df.columns.str.strip()
        
        count = 0
        for _, row in df.iterrows():
            kode = str(row['Nomor SKU']).strip()
            # Skip empty rows
            if kode == 'nan' or not kode: continue
            
            nama = str(row['Nama Produk']).strip()
            if nama == 'nan': nama = "Tanpa Nama"
            
            # Extract harga_modal safely and handle Pandas NaN
            modal = 0.0
            if 'Rata-Rata Modal Bobot' in df.columns:
                val = row['Rata-Rata Modal Bobot']
                # pd.notna() checks if the value is NOT empty/NaN
                if pd.notna(val): 
                    try: 
                        modal = float(val)
                    except (ValueError, TypeError): 
                        pass
            
            # Check if SKU already exists to prevent duplicates
            existing = db.query(SkuMaster).filter(SkuMaster.kode_sku == kode).first()
            if not existing:
                sku = SkuMaster(kode_sku=kode, nama_produk=nama, harga_modal=modal)
                db.add(sku)
                count += 1
                
        db.commit()
        print(f"  -> Successfully imported {count} SKUs into the unified database.")
    except Exception as e:
        print(f"  -> Error migrating SKUs: {e}")
        db.rollback() # Rollback the transaction so it doesn't lock the database

def _get_alembic_config():
    """Build an Alembic Config pointing at this project's alembic.ini, with the
    migrations folder resolved absolutely so it works regardless of CWD.
    """
    alembic_cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location", os.path.join(BASE_DIR, "data", "migrations")
    )
    return alembic_cfg


def stamp_baseline(revision: str = "c9b50081130a"):
    """Mark an EXISTING database as already being at `revision`, WITHOUT
    running that migration's DDL.

    Use this ONCE when the tables were created outside Alembic (e.g. via
    Base.metadata.create_all) so Alembic has no version recorded and would
    otherwise try to re-create tables that already exist. This only writes a
    row into the `alembic_version` table -- it does not touch your data.
    """
    print(f"=== ALEMBIC STAMP BASELINE -> {revision} ===")
    command.stamp(_get_alembic_config(), revision)
    print("=== STAMP COMPLETE (Alembic now knows the baseline is applied) ===")


def run_alembic_upgrade():
    """Apply all pending Alembic schema migrations up to the latest (head).

    This is what actually creates/updates tables such as `profit_history`.
    Safe to run repeatedly: already-applied revisions are skipped.
    """
    print("=== ALEMBIC SCHEMA MIGRATION: upgrade -> head ===")
    command.upgrade(_get_alembic_config(), "head")
    print("=== SCHEMA MIGRATION COMPLETE (now at head) ===")


def run_data_seed():
    """Legacy ONE-TIME data import from JSON/Excel into the database.

    WARNING: re-running this creates DUPLICATE persons/balances because
    migrate_persons_and_balances() has no de-duplication guard. Only run
    this on a fresh / empty database.
    """
    print("=== ESSA STORE DATA SEED: STAGE 1 ===")
    db = SessionLocal()
    try:
        migrate_settings(db)
        migrate_persons_and_balances(db)
        migrate_skus(db)
        print("\n=== STAGE 1 COMPLETE ===")
    finally:
        db.close()


if __name__ == "__main__":
    # Default: run schema migrations only (safe to run repeatedly).
    #
    # `--stamp-baseline` : run ONCE on a pre-existing DB whose tables were
    #                      created outside Alembic, so Alembic records the
    #                      initial schema as already applied.
    # `--seed`           : run ONLY on a fresh database to import legacy
    #                      JSON/Excel data (creates duplicates if re-run).
    if "--seed" in sys.argv:
        run_data_seed()
    elif "--stamp-baseline" in sys.argv:
        stamp_baseline()
    else:
        run_alembic_upgrade()