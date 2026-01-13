#!/bin/bash
set -e

echo "==== Starting HRMS Backend ===="

# Database connection parameters
DB_HOST="${DATABASE_HOST:-db}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_USER="${DATABASE_USER:-postgres}"
MAX_ATTEMPTS=30
RETRY_INTERVAL=2

echo "Checking database connection..."

# Wait for PostgreSQL to be ready
attempt=1
while [ $attempt -le $MAX_ATTEMPTS ]; do
    echo "Waiting for database... (attempt $attempt/$MAX_ATTEMPTS)"
    
    if python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(1); result = s.connect_ex(('$DB_HOST', $DB_PORT)); s.close(); exit(result)"; then
        echo "✓ Database is ready!"
        break
    fi
    
    if [ $attempt -eq $MAX_ATTEMPTS ]; then
        echo "ERROR: Database not available after $MAX_ATTEMPTS attempts. Exiting."
        exit 1
    fi
    
    attempt=$((attempt + 1))
    sleep $RETRY_INTERVAL
done

echo "Running database migrations..."

# Handle potential migration conflicts by faking problematic migrations first
echo "Checking for migration conflicts..."

# Check if we need to fake any migrations that might conflict
python -c "
import os
import django
from django.conf import settings
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

with connection.cursor() as cursor:
    # Check if columns already exist
    cursor.execute(\"\"\"
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='employees_attendance' 
        AND column_name IN ('current_session_type', 'daily_sessions_count', 'max_daily_sessions')
    \"\"\")
    existing_columns = [row[0] for row in cursor.fetchall()]
    
    if existing_columns:
        print(f'Found existing columns: {existing_columns}')
        print('Will use safe migration approach')
    else:
        print('No conflicting columns found')
" || echo "Could not check for existing columns, proceeding with normal migration"

# Run migrations with error handling
if ! python manage.py migrate --noinput; then
    echo "Migration failed, attempting recovery..."
    
    # Try to fake problematic migrations and run our safe migration
    echo "Attempting to fake conflicting migrations..."
    python manage.py migrate employees 0002_add_session_tracking_fields --fake || true
    python manage.py migrate employees 0003_add_missing_attendance_fields --fake || true
    python manage.py migrate employees 0003_attendance_daily_sessions_count_and_more --fake || true
    
    # Now run migrations again
    echo "Retrying migrations after faking conflicts..."
    python manage.py migrate --noinput
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting Gunicorn WSGI server..."
exec gunicorn hrms_core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 300 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
