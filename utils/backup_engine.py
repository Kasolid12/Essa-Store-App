# app_essa/utils/backup_engine.py
import os
import sqlite3
from datetime import datetime

def backup_database():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "essa.db")
    
    if not os.path.exists(db_path): return False

    backup_dir = os.path.join(base_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filepath = os.path.join(backup_dir, f"essa_backup_{timestamp}.db")

    try:
        # [SOLUSI] Gunakan API Backup bawaan SQLite yang 100% aman dari korupsi data
        with sqlite3.connect(db_path) as source:
            with sqlite3.connect(backup_filepath) as target:
                source.backup(target)
                
        print(f"System Backup Successful: essa_backup_{timestamp}.db")
        _cleanup_old_backups(backup_dir, keep_limit=30)
        return True
    except Exception as e:
        print(f"CRITICAL BACKUP FAILED: {e}")
        return False

def _cleanup_old_backups(backup_dir, keep_limit=30):
    """Silently deletes old backups to save hard drive space."""
    backups = []
    
    # Gather all backup files
    for file in os.listdir(backup_dir):
        if file.startswith("essa_backup_") and file.endswith(".db"):
            full_path = os.path.join(backup_dir, file)
            backups.append((os.path.getctime(full_path), full_path))
    
    # Sort by creation time (Oldest first)
    backups.sort()
    
    # Delete the oldest files if we exceed the limit
    if len(backups) > keep_limit:
        files_to_delete = len(backups) - keep_limit
        for i in range(files_to_delete):
            try:
                os.remove(backups[i][1])
            except Exception:
                pass