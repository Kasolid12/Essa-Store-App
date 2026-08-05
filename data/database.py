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

def get_cloud_engine():
    """Kembalikan engine Postgres cloud. None bila CLOUD_DATABASE_URL belum diisi."""
    global _cloud_engine
    url = os.environ.get("CLOUD_DATABASE_URL", "").strip()
    if not url:
        return None
    if _cloud_engine is None:
        _cloud_engine = create_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},  # jangan menggantung lama saat app ditutup
        )
    return _cloud_engine

def get_cloud_session():
    """Buat session baru ke database cloud (Neon)."""
    eng = get_cloud_engine()
    if eng is None:
        raise RuntimeError("CLOUD_DATABASE_URL belum diatur di file .env")
    Session = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return Session()