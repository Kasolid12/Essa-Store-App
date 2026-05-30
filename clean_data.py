import sqlite3
import os

def clean_transactional_data():
    db_path = 'essa.db'
    if not os.path.exists(db_path):
        print(f"❌ Error: Database '{db_path}' tidak ditemukan!")
        return

    print("⚠️ PERINGATAN: Script ini akan MENGHAPUS SEMUA DATA TRANSAKSI.")
    print("Master Data (SKU, Person, Tarif) AKAN DIPERTAHANKAN.")
    konfirmasi = input("Ketik 'YAKIN' untuk melanjutkan: ")
    
    if konfirmasi != 'YAKIN':
        print("Operasi dibatalkan.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tabel_transaksi = [
        'debt_entries',
        'debt_payments',
        'hasil_cutting',
        'distribusi_cutting',
        'pengeluaran_offline',
        'modal_operasional',
        'bon_balances',
        'bon_movements',
        'salary_runs',
        'salary_line_items',
        'pengsup_reconciliations',
        'invoice_headers',
        'invoice_items',
        'invoice_payments',
        'stock_audit'
    ]

    for tabel in tabel_transaksi:
        try:
            # Coba hapus isi tabel
            cursor.execute(f"DELETE FROM {tabel}")
            
            # Coba reset urutan ID (Auto-Increment)
            try:
                cursor.execute(f"UPDATE sqlite_sequence SET seq = 0 WHERE name = '{tabel}'")
            except sqlite3.OperationalError:
                pass # Abaikan jika tabel tidak memiliki auto-increment
                
            print(f"🧹 Tabel '{tabel}' berhasil dikosongkan.")
            
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                print(f"⚠️ Tabel '{tabel}' tidak ditemukan di database. Melewati...")
            else:
                print(f"❌ Error pada tabel '{tabel}': {e}")

    conn.commit()
    conn.close()
    print("\n✅ BERHASIL! Database telah bersih secara maksimal dan siap digunakan untuk Production.")

if __name__ == '__main__':
    clean_transactional_data()