import sys
import pandas as pd
import math

from data.database import SessionLocal
from data.models import SkuMaster
from data.models.master import TarifMaster
from data.models.salary import MasterTarifPenjahit

def clean_nan(val, default_val=0.0):
    if pd.isna(val) or math.isnan(val):
        return default_val
    return float(val)

def clean_text(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def import_master_tarif(excel_file_path):
    print(f"[*] Memulai import data dari {excel_file_path}...")
    db = SessionLocal()
    
    try:
        # ==========================================
        # 1. IMPORT SHEET PENG-SUP (SKU_Pengsup)
        # ==========================================
        print("[*] Membaca Sheet: SKU_Pengsup...")
        try:
            df_pengsup = pd.read_excel(excel_file_path, sheet_name='SKU_Pengsup')
            
            for index, row in df_pengsup.iterrows():
                kode_sku = clean_text(row.get('Nomor SKU'))
                
                if not kode_sku or kode_sku.lower() == 'nan':
                    continue
                
                kain = clean_nan(row.get('Kain'))
                potongan = clean_nan(row.get('Potongan'))

                # 1A. SkuMaster
                sku = db.query(SkuMaster).filter(SkuMaster.kode_sku == kode_sku).first()
                if not sku:
                    sku = SkuMaster(kode_sku=kode_sku, nama_produk=kode_sku)
                    db.add(sku)
                    db.flush()
                
                # 1B. TarifMaster (Update tarif pengsup kain & potongan sesuai model master.md)
                tarif = db.query(TarifMaster).filter(TarifMaster.kode_sku == kode_sku).first()
                if not tarif:
                    tarif = TarifMaster(
                        kode_sku=kode_sku,
                        tarif_pengsup_kain=kain,
                        tarif_pengsup_potongan=potongan
                    )
                    db.add(tarif)
                else:
                    tarif.tarif_pengsup_kain = kain
                    tarif.tarif_pengsup_potongan = potongan
            
            print(f"[✓] Berhasil memproses data Pengsup ({len(df_pengsup)} baris).")
        except ValueError:
            print("[-] Peringatan: Sheet 'SKU_Pengsup' tidak ditemukan di Excel, dilewati.")

        # ==========================================
        # 2. IMPORT SHEET PENJAHIT (SKU_Penjahit)
        # ==========================================
        print("\n[*] Membaca Sheet: SKU_Penjahit...")
        try:
            df_penjahit = pd.read_excel(excel_file_path, sheet_name='SKU_Penjahit')
            
            for index, row in df_penjahit.iterrows():
                kode_sku = clean_text(row.get('SKU'))
                
                if not kode_sku or kode_sku.lower() == 'nan':
                    continue
                
                harga_satuan = clean_nan(row.get('Harga Satuan'))

                # 2A. SkuMaster
                sku = db.query(SkuMaster).filter(SkuMaster.kode_sku == kode_sku).first()
                if not sku:
                    sku = SkuMaster(kode_sku=kode_sku, nama_produk=f"Produk {kode_sku}")
                    db.add(sku)
                    db.flush()
                
                # 2B. TarifMaster (Update tarif_jahit sesuai model master.md)
                tarif = db.query(TarifMaster).filter(TarifMaster.kode_sku == kode_sku).first()
                if not tarif:
                    tarif = TarifMaster(
                        kode_sku=kode_sku,
                        tarif_jahit=harga_satuan
                    )
                    db.add(tarif)
                else:
                    tarif.tarif_jahit = harga_satuan

                # 2C. MasterTarifPenjahit (Update tabel khusus untuk Gaji Penjahit sesuai salary.md)
                mtp = db.query(MasterTarifPenjahit).filter(MasterTarifPenjahit.kode_garapan == kode_sku).first()
                if not mtp:
                    mtp = MasterTarifPenjahit(
                        kode_garapan=kode_sku,
                        harga=harga_satuan
                    )
                    db.add(mtp)
                else:
                    mtp.harga = harga_satuan
            
            print(f"[✓] Berhasil memproses data Penjahit ({len(df_penjahit)} baris).")
        except ValueError:
            print("[-] Peringatan: Sheet 'SKU_Penjahit' tidak ditemukan di Excel, dilewati.")

        db.commit()
        print("\n[★] IMPORT DATABASE SELESAI DAN SUKSES DISIMPAN! [★]")

    except Exception as e:
        db.rollback()
        print(f"\n[!] TERJADI KESALAHAN FATAL: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    NAMA_FILE_EXCEL = "Master_tarif.xlsx" # Pastikan nama file excelnya sudah benar
    
    print("=== ESSA STORE: MASTER DATA MIGRATION TOOL ===")
    import_master_tarif(NAMA_FILE_EXCEL)