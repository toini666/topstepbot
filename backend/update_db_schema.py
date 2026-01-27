import sqlite3
import os

# Try both potential locations
db_paths = [
    "/Users/awagon/Documents/dev/topstepbot/backend/topstepbot.db",
    "/Users/awagon/Documents/dev/topstepbot/topstepbot.db"
]

db_path = None
for path in db_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    print("Database not found in standard locations.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Update Discord Settings Table
table = "discord_notification_settings"
columns_to_add = [
    ("notify_partial_close", "BOOLEAN DEFAULT 1"), # SQLite uses 1 for True
]

print(f"Updating database at {db_path}...")

for col_name, col_type in columns_to_add:
    try:
        print(f"Adding column '{col_name}' to {table}...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
        print(f"  - Success.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print(f"  - Column '{col_name}' already exists.")
        else:
            print(f"  - Error adding '{col_name}': {e}")
            # If table doesn't exist, that's fine too (it will be created by init_db next run if needed)
            if "no such table" in str(e):
                 print(f"  - Table {table} does not exist. Skipping.")

conn.commit()
conn.close()
print("Database schema update complete.")
