import sqlite3
import os

def run_migration():
    # Pastikan database ada di folder yang sama
    db_path = 'essa.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} tidak ditemukan!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Memulai Migrasi Database untuk Profit Dashboard...")

    # 1. Update tabel debt_entries (Modal Hutang)
    try:
        cursor.execute("ALTER TABLE debt_entries ADD COLUMN status_cutting VARCHAR DEFAULT 'OPEN'")
        print("✅ Berhasil menambahkan kolom 'status_cutting' ke tabel debt_entries.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️ Kolom 'status_cutting' sudah ada. Melewati...")
        else:
            print(f"❌ Error pada debt_entries: {e}")

    # 2. Update tabel hasil_cutting
    try:
        cursor.execute("ALTER TABLE hasil_cutting ADD COLUMN modal_hutang_id INTEGER")
        print("✅ Berhasil menambahkan kolom 'modal_hutang_id' ke tabel hasil_cutting.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️ Kolom 'modal_hutang_id' sudah ada. Melewati...")
        else:
            print(f"❌ Error pada hasil_cutting: {e}")

    # 3. Update tabel distribusi_cutting
    try:
        cursor.execute("ALTER TABLE distribusi_cutting ADD COLUMN hasil_cutting_id INTEGER")
        print("✅ Berhasil menambahkan kolom 'hasil_cutting_id' ke tabel distribusi_cutting.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️ Kolom 'hasil_cutting_id' sudah ada. Melewati...")
        else:
            print(f"❌ Error pada distribusi_cutting: {e}")

    conn.commit()
    conn.close()
    print("\n🚀 Migrasi Selesai! Database siap digunakan untuk Profit Simulation.")

if __name__ == '__main__':
    run_migration()