import sqlite3
import os

def run_migration():
    db_path = 'essa.db'
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} tidak ditemukan!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Memulai penambahan kolom 'kode_produksi'...")
    tabel_target = ['debt_entries', 'hasil_cutting', 'distribusi_cutting']

    for tabel in tabel_target:
        try:
            cursor.execute(f"ALTER TABLE {tabel} ADD COLUMN kode_produksi VARCHAR")
            print(f"✅ Berhasil menambahkan 'kode_produksi' ke tabel {tabel}.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"⚠️ Kolom 'kode_produksi' sudah ada di {tabel}. Melewati...")
            else:
                print(f"❌ Error pada {tabel}: {e}")

    conn.commit()
    conn.close()
    print("\n🚀 Migrasi Tahap 1 Selesai! Database siap menggunakan sistem Kode Produksi.")

if __name__ == '__main__':
    run_migration()