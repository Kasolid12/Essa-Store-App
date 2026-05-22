# app_essa/utils/backup_engine.py
import os
import shutil
from datetime import datetime

def backup_database():
    """Creates a timestamped backup of the SQLite database and cleans up old ones."""
    # 1. Locate the active database
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "essa.db")
    
    if not os.path.exists(db_path):
        print("Backup Error: Database file not found.")
        return False

    # 2. Setup the Backup Directory
    backup_dir = os.path.join(base_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    # 3. Generate Timestamped Filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"essa_backup_{timestamp}.db"
    backup_filepath = os.path.join(backup_dir, backup_filename)

    try:
        # 4. Copy the Database
        shutil.copy2(db_path, backup_filepath)
        print(f"System Backup Successful: {backup_filename}")
        
        # 5. Run Smart Cleanup (Keep only last 30 backups)
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