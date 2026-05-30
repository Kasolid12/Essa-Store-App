import sqlite3
import pandas as pd
import os
from datetime import datetime

def run_import():
    db_path = 'essa.db'
    excel_path = 'MasterSKU.xlsx'

    if not os.path.exists(excel_path):
        print(f"❌ Error: File '{excel_path}' tidak ditemukan di folder ini!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(sku_master)")
    columns_info = cursor.fetchall()
    
    if not columns_info:
        print("❌ Error: Tabel 'sku_master' tidak ditemukan!")
        return

    print("1. Membersihkan data SKU lama...")
    cursor.execute("DELETE FROM sku_master")
    try:
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'sku_master'")
    except:
        pass

    print("2. Membaca file MasterSKU.xlsx...")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"❌ Gagal membaca Excel: {e}")
        return

    df.columns = df.columns.str.strip()
    
    col_sku = next((c for c in df.columns if 'sku' in c.lower()), 'Nomor SKU')
    col_nama = next((c for c in df.columns if 'nama' in c.lower() or 'judul' in c.lower()), 'Nama Produk')
    col_modal = next((c for c in df.columns if 'modal' in c.lower() or 'bobot' in c.lower()), 'Rata-Rata Modal Bobot')

    print(f"-> Memetakan '{col_sku}' ke Kode SKU")
    print(f"-> Memetakan '{col_nama}' ke Nama Produk")
    print(f"-> Memetakan '{col_modal}' ke Harga Modal & Harga Jual (Simulasi)")

    berhasil = 0
    gagal = 0
    waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for index, row in df.iterrows():
        sku = str(row[col_sku]).strip() if pd.notna(row[col_sku]) else ""
        nama = str(row[col_nama]).strip() if pd.notna(row[col_nama]) else ""
        
        modal = 0.0
        if col_modal in df.columns and pd.notna(row[col_modal]):
            val = row[col_modal]
            if isinstance(val, (int, float)):
                modal = float(val)
            else:
                try:
                    modal_str = str(val).replace('Rp', '').replace(' ', '')
                    if modal_str.count('.') == 1 and len(modal_str.split('.')[-1]) == 3:
                        modal_str = modal_str.replace('.', '')
                    elif modal_str.count('.') > 1:
                        modal_str = modal_str.replace('.', '')
                    modal = float(modal_str.replace(',', ''))
                except ValueError:
                    modal = 0.0
        
        if sku and sku.lower() != "nan":
            insert_data = {}
            
            for col in columns_info:
                col_name = col[1]
                col_type = col[2].upper() if col[2] else "TEXT"
                
                if col_name == 'id': continue 
                elif col_name == 'kode_sku': insert_data[col_name] = sku
                elif col_name == 'nama_produk': insert_data[col_name] = nama
                elif col_name == 'harga_modal': insert_data[col_name] = modal
                
                # --- PERBAIKAN: Menggunakan Harga Modal sebagai Harga Jual (Simulasi) ---
                elif col_name == 'harga_jual': insert_data[col_name] = modal
                # -----------------------------------------------------------------------
                
                elif col_name == 'kain_cost': insert_data[col_name] = modal
                elif col_name == 'potongan_cost': insert_data[col_name] = 0.0
                elif col_name == 'is_active': insert_data[col_name] = 1
                elif col_name == 'is_deleted': insert_data[col_name] = 0
                elif col_name in ['created_at', 'updated_at'] or 'DATE' in col_type or 'TIME' in col_type:
                    insert_data[col_name] = waktu_sekarang
                else:
                    if 'INT' in col_type or 'FLOAT' in col_type or 'REAL' in col_type or 'NUM' in col_type:
                        insert_data[col_name] = 0
                    else:
                        insert_data[col_name] = "-"
            
            cols = ", ".join(insert_data.keys())
            placeholders = ", ".join(["?"] * len(insert_data))
            values = tuple(insert_data.values())
            update_clause = ", ".join([f"{k}=excluded.{k}" for k in insert_data.keys() if k != 'kode_sku'])
            
            query = f"""
                INSERT INTO sku_master ({cols})
                VALUES ({placeholders})
                ON CONFLICT(kode_sku) DO UPDATE SET {update_clause}
            """
            
            try:
                cursor.execute(query, values)
                berhasil += 1
            except Exception as e:
                print(f"❌ Error pada SKU '{sku}': {e}")
                gagal += 1

    conn.commit()
    conn.close()
    print(f"\n✅ SELESAI! {berhasil} SKU sukses diimpor dengan Harga Jual = Harga Modal.")

if __name__ == '__main__':
    run_import()