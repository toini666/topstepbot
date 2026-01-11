import sqlite3
import os

db_path = "/Users/awagon/Documents/dev/topstepbot/backend/topstepbot.db"

if not os.path.exists(db_path):
    # Try one level up
    db_path = "/Users/awagon/Documents/dev/topstepbot/topstepbot.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

columns_to_add = [
    ("exit_price", "FLOAT"),
    ("fees", "FLOAT"),
    ("session", "VARCHAR"),
    ("duration_seconds", "INTEGER")
]

print(f"Updating database at {db_path}...")

for col_name, col_type in columns_to_add:
    try:
        print(f"Adding column '{col_name}'...")
        cursor.execute(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}")
        print(f"  - Success.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print(f"  - Column '{col_name}' already exists.")
        else:
            print(f"  - Error adding '{col_name}': {e}")

conn.commit()
conn.close()
print("Database schema update complete.")
