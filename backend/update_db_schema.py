import sqlite3
import os

# Try both potential locations
db_paths = [
    "/Users/awagon/Documents/dev/topstepbot/backend/topstepbot.db",
    "/Users/awagon/Documents/dev/topstepbot/topstepbot.db"
]

# Prefer a non-empty DB file. The backend/topstepbot.db can be a 0-byte stub
# while the actual database lives at the project root.
db_path = None
for path in db_paths:
    if os.path.exists(path) and os.path.getsize(path) > 0:
        db_path = path
        break

if not db_path:
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break

if not db_path:
    print("Database not found in standard locations.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"Updating database at {db_path}...")


def add_columns(table: str, columns_to_add: list[tuple[str, str]]) -> None:
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
                if "no such table" in str(e):
                    print(f"  - Table {table} does not exist. Skipping.")


# Update Discord Settings Table
add_columns(
    "discord_notification_settings",
    [
        ("notify_partial_close", "BOOLEAN DEFAULT 1"),  # SQLite uses 1 for True
    ],
)

# Update Account Settings Table
add_columns(
    "account_settings",
    [
        ("allow_min_contract_over_risk", "BOOLEAN DEFAULT 0"),
    ],
)

conn.commit()
conn.close()
print("Database schema update complete.")
