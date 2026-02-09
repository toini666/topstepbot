#!/bin/bash
set -e

echo "================================================="
echo "   TopStepBot Docker Container Starting"
echo "================================================="

# Ensure data directory exists
mkdir -p /app/data/backups

# Set default environment variables for Docker paths
export DATABASE_URL="${DATABASE_URL:-sqlite:////app/data/topstepbot.db}"
export PERSISTENCE_FILE="${PERSISTENCE_FILE:-/app/data/persistence.json}"
export CALENDAR_CACHE_FILE="${CALENDAR_CACHE_FILE:-/app/data/calendar_cache.json}"
export BACKUP_DIR="${BACKUP_DIR:-/app/data/backups}"

echo "Database: $DATABASE_URL"
echo "Data dir: /app/data/"

# Initialize database (idempotent)
python -c "
from backend.database import init_db
init_db()
print('Database initialized.')
"

echo "================================================="
echo "Starting services..."
echo "Dashboard: http://localhost:8080"
echo "================================================="

# Execute the CMD (supervisord)
exec "$@"
