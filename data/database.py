import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session

try:
    from dotenv import load_dotenv  # opsional — .env dilewati jika belum terinstall
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

# Muat konfigurasi dari file .env (jika ada) — jangan simpan secret di kode.
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─────────────────────────────────────────────────────────────────────
# ENGINE APLIKASI — WAJIB SQLite lokal (offline-first).
# Aplikasi tidak boleh bergantung pada ketersediaan internet/cloud.
# Bisa di-override lewat env APP_DATABASE_URL untuk keperluan uji coba saja.
# ─────────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "APP_DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'essa.db')}",
)

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# PRAGMA hanya berlaku untuk SQLite — Postgres tidak mengenal perintah ini.
# (Guard by dialect: bila APP_DATABASE_URL menunjuk ke Postgres, blok ini dilewati.)
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Tunggu maks. 5 detik bila DB sedang dikunci proses lain
        # (mis. auto-pull cloud di thread latar saat app baru dibuka).
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

# Session Factory untuk database aplikasi
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = scoped_session(session_factory)

def get_db():
    """Dependency untuk mendapatkan session database aplikasi."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────────────
# ENGINE CLOUD (Neon PostgreSQL) — HANYA untuk skrip sinkronisasi &
# migrasi cloud (Fase 3-6 panduan). Tidak dipakai jalur utama aplikasi.
# URL dibaca lazy dari env agar perubahan .env langsung terlihat.
# ─────────────────────────────────────────────────────────────────────
_cloud_engine = None
_cloud_engine_failed = False   # True bila driver cloud hilang — pesan dicetak sekali saja

def get_cloud_engine():
    """Kembalikan engine Postgres cloud. None bila CLOUD_DATABASE_URL belum diisi
    ATAU driver Postgres (psycopg2) tidak terpasang di interpreter ini."""
    global _cloud_engine, _cloud_engine_failed
    url = os.environ.get("CLOUD_DATABASE_URL", "").strip()
    if not url:
        return None
    if _cloud_engine is None and not _cloud_engine_failed:
        _kwargs = {"echo": False, "pool_pre_ping": True}
        # connect_timeout hanya dikenal driver Postgres (psycopg2).
        # Untuk URL non-Postgres (mis. SQLite saat uji coba) jangan dikirim.
        if "postgres" in url:
            _kwargs["connect_args"] = {"connect_timeout": 5}
        try:
            _cloud_engine = create_engine(url, **_kwargs)
        except ImportError as e:
            # Driver Postgres (psycopg2) belum terpasang di interpreter ini.
            # Terjadi bila aplikasi dibuka lewat double-click main.py — Windows
            # memakai Python lain (tanpa dependensi aplikasi). Jangan crash:
            # laporkan SEKALI dengan jelas, lalu biarkan status cloud "NONAKTIF".
            print(
                "[CloudSync] Cloud nonaktif: driver database cloud belum "
                f"terpasang ({e}).\n"
                "            Buka aplikasi lewat start_app.bat, atau install "
                "dependensi:\n"
                "            pip install -r requirements.txt"
            )
            _cloud_engine_failed = True
            return None
    return _cloud_engine

def get_cloud_session():
    """Buat session baru ke database cloud (Neon)."""
    eng = get_cloud_engine()
    if eng is None:
        raise RuntimeError("CLOUD_DATABASE_URL belum diatur di file .env")
    Session = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return Session()