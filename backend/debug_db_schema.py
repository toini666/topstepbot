import sqlite3
import os

db_path = "/Users/awagon/Documents/dev/topstepbot/backend/topstepbot.db"

if not os.path.exists(db_path):
    # Try one level up if not found (relative path issue potential)
    db_path = "/Users/awagon/Documents/dev/topstepbot/topstepbot.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(trades)")
        columns = cursor.fetchall()
        print("Columns in 'trades' table:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
    except Exception as e:
        print(f"Error reading DB: {e}")
    finally:
        conn.close()
