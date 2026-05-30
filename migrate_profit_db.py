import sqlite3

def run_migration():
    conn = sqlite3.connect('essa.db')
    cursor = conn.cursor()
    try:
        # Tambahkan kolom status_cutting dengan nilai default 'OPEN'
        cursor.execute("ALTER TABLE debt_entries ADD COLUMN status_cutting VARCHAR DEFAULT 'OPEN'")
        print("✅ Berhasil menambahkan kolom 'status_cutting' ke tabel debt_entries.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("⚠️ Kolom 'status_cutting' sudah ada. Aman!")
        else:
            print(f"❌ Error: {e}")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    run_migration()