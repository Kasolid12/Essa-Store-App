#!/usr/bin/env python3
"""
Yazmina Hijab Web — Development Setup Script.

Safe to run multiple times (idempotent):
- Creates all DB tables if not exist
- Creates default admin if no admin exists
- Does NOT overwrite existing admin

Usage:
  python setup_dev.py                    # Interactive (asks for password)
  python setup_dev.py --auto             # Non-interactive (default admin/admin123)
  python setup_dev.py --user bob --pass secret123
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.database import engine, SessionLocal, Base
from app.models.admin_user import AdminUser
from app.auth import hash_password


def setup_database():
    """Create all tables (safe — only creates missing ones)."""
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables verified.")


def setup_admin(username="admin", password="admin123", interactive=True):
    """Create admin user if none exists."""
    db = SessionLocal()
    try:
        existing = db.query(AdminUser).first()
        if existing:
            print(f"[OK] Admin '{existing.username}' already exists. Skipped.")
            return True

        if interactive:
            import getpass
            print("\n--- Create Admin User ---")
            username = input(f"Username [{username}]: ").strip() or username
            password = getpass.getpass("Password: ")
            if len(password) < 6:
                print("[X] Password minimal 6 karakter.")
                return False
            confirm = getpass.getpass("Konfirmasi password: ")
            if password != confirm:
                print("[X] Password tidak cocok.")
                return False

        admin = AdminUser(
            username=username,
            password_hash=hash_password(password),
        )
        db.add(admin)
        db.commit()
        print(f"[OK] Admin '{username}' created successfully.")
        return True

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Yazmina Hijab Web — Dev Setup")
    parser.add_argument("--auto", action="store_true", help="Non-interactive mode (default admin/admin123)")
    parser.add_argument("--user", default="admin", help="Admin username (default: admin)")
    parser.add_argument("--pass", dest="password", default="admin123", help="Admin password (default: admin123)")
    args = parser.parse_args()

    settings = get_settings()
    print(f"=== Yazmina Hijab Web — Setup ===")
    print(f"App: {settings.APP_NAME} v{settings.APP_VERSION}")
    print()

    # 1. Create tables
    setup_database()

    # 2. Create admin
    interactive = not args.auto
    setup_admin(
        username=args.user,
        password=args.password,
        interactive=interactive,
    )

    print()
    print("Setup complete! You can now run: uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
