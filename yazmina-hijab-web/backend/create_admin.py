#!/usr/bin/env python3
"""
Create admin user for Yazmina Hijab Web.
Safe to run multiple times — skips if admin already exists.

Usage:
  python create_admin.py                    # Interactive
  python create_admin.py --auto             # Default admin/admin123
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.database import engine, SessionLocal, Base
from app.models.admin_user import AdminUser
from app.auth import hash_password


def main():
    parser = argparse.ArgumentParser(description="Create admin user")
    parser.add_argument("--auto", action="store_true", help="Non-interactive (default admin/admin123)")
    parser.add_argument("--user", default="admin", help="Username (default: admin)")
    parser.add_argument("--pass", dest="password", default="admin123", help="Password (default: admin123)")
    args = parser.parse_args()

    settings = get_settings()
    print("=== Yazmina Hijab - Create Admin User ===")
    db_label = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "local SQLite"
    print(f"Database: {db_label}")
    print()

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(AdminUser).first()
        if existing:
            print(f"[OK] Admin '{existing.username}' already exists. Skipped.")
            return

        if args.auto:
            username = args.user
            password = args.password
        else:
            username = input(f"Username admin [{args.user}]: ").strip() or args.user
            import getpass
            password = getpass.getpass("Password: ")
            if len(password) < 6:
                print("[X] Password minimal 6 karakter.")
                return
            confirm = getpass.getpass("Konfirmasi password: ")
            if password != confirm:
                print("[X] Password tidak cocok.")
                return

        admin = AdminUser(
            username=username,
            password_hash=hash_password(password),
        )
        db.add(admin)
        db.commit()
        print(f"\n[OK] Admin '{username}' created successfully!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
