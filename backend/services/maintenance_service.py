import shutil
import os
import datetime
from backend.database import DATABASE_URL, SessionLocal, Log
from sqlalchemy import text

# Extract path from sqlite:///./topstepbot.db
DB_FILE_PATH = DATABASE_URL.replace("sqlite:///", "")
BACKUP_DIR = "backups"

def backup_database():
    """
    Creates a timestamped backup of the database.
    Keeps only the last 7 backups.
    """
    try:
        # Ensure backup directory exists
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            print(f"Created backup directory: {BACKUP_DIR}")

        # Create filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"topstepbot_backup_{timestamp}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        # Copy file
        if os.path.exists(DB_FILE_PATH):
            shutil.copy2(DB_FILE_PATH, backup_path)
            print(f"✅ Database backed up to {backup_path}")
            _log_maintenance(f"Database backed up: {backup_filename}")
        else:
            print(f"❌ Database file not found at {DB_FILE_PATH}")
            _log_maintenance("Backup failed: source DB not found", level="ERROR")
            return

        # Cleanup old backups (Keep last 7)
        _cleanup_old_backups()

    except Exception as e:
        print(f"❌ Backup failed: {e}")
        _log_maintenance(f"Backup failed: {e}", level="ERROR")

def _cleanup_old_backups(keep=7):
    """
    Removes old backup files, keeping only the 'keep' most recent ones.
    """
    try:
        files = [
            os.path.join(BACKUP_DIR, f) 
            for f in os.listdir(BACKUP_DIR) 
            if f.startswith("topstepbot_backup_") and f.endswith(".db")
        ]
        files.sort(key=os.path.getmtime, reverse=True) # Newest first

        if len(files) > keep:
            for old_file in files[keep:]:
                os.remove(old_file)
                print(f"🗑️ Removed old backup: {old_file}")
                
    except Exception as e:
        print(f"Warning: Failed to cleanup old backups: {e}")

def clean_logs(days=7):
    """
    Deletes logs older than 'days' from the database.
    """
    db = SessionLocal()
    try:
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        
        # SQLAlchemy core delete for efficiency or ORM
        # Using ORM for simplicity or raw SQL for speed
        deleted_count = db.query(Log).filter(Log.timestamp < cutoff_date).delete(synchronize_session=False)
        db.commit()
        
        if deleted_count > 0:
            msg = f"Cleaned {deleted_count} logs older than {days} days."
            print(f"🧹 {msg}")
            # Log the cleaning action itself (careful not to loop if retention is extremely short, but 7 days is fine)
            # We add a new log entry AFTER cleaning
            db.add(Log(level="INFO", message=msg))
            db.commit()
        else:
            print("🧹 Logs clean. Nothing to delete.")

    except Exception as e:
        print(f"❌ Log cleaning failed: {e}")
        db.rollback()
    finally:
        db.close()

def _log_maintenance(message, level="INFO"):
    """
    Helper to log maintenance actions to the DB.
    """
    db = SessionLocal()
    try:
        db.add(Log(level=level, message=message))
        db.commit()
    except Exception:
        pass # If logging fails, just ignore to avoid loops
    finally:
        db.close()

def check_and_run_startup_backup():
    """
    Checks if a backup has been performed today.
    If not, triggers a backup immediately.
    """
    try:
        today_str = datetime.datetime.now().strftime("%Y%m%d")
        
        # Check if backup dir exists
        if not os.path.exists(BACKUP_DIR):
            print("Startup Backup: Directory missing, running backup...")
            backup_database()
            return

        # List files
        files = os.listdir(BACKUP_DIR)
        
        # Check for matching prefix
        backup_exists = any(f.startswith(f"topstepbot_backup_{today_str}") for f in files)
        
        if not backup_exists:
            print(f"⚠️ No backup found for today ({today_str}). Running startup backup...")
            backup_database()
        else:
            print(f"✅ Backup for today ({today_str}) already exists.")
            
    except Exception as e:
        print(f"❌ Startup backup check failed: {e}")
