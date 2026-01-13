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
echo "🔍 Checking migration state and handling conflicts..."

# Enhanced migration handling with better error recovery
python -c "
import os
import sys
import django
from django.conf import settings
from django.db import connection
from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

print('📊 Checking database and migration state...')

try:
    with connection.cursor() as cursor:
        # Check if employees_attendance table exists
        cursor.execute(\"\"\"
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'employees_attendance'
        \"\"\")
        
        if cursor.fetchone():
            print('✅ employees_attendance table exists')
            
            # Check existing columns
            cursor.execute(\"\"\"
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='employees_attendance' 
                AND column_name IN ('current_session_type', 'daily_sessions_count', 'max_daily_sessions', 'total_working_hours')
            \"\"\")
            existing_columns = [row[0] for row in cursor.fetchall()]
            print(f'📋 Existing columns: {existing_columns}')
            
            if len(existing_columns) >= 3:
                print('🎯 Database appears to have session tracking columns')
                print('Will use safe migration approach')
            else:
                print('📝 Database missing some columns, normal migration should work')
        else:
            print('📝 employees_attendance table does not exist, normal migration should work')
            
except Exception as e:
    print(f'⚠️ Could not check database state: {e}')
    print('Proceeding with normal migration')
" || echo "Could not check database state, proceeding with migration"

# Try normal migration first
echo "🚀 Attempting normal migration..."
if python manage.py migrate --noinput; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Normal migration failed, attempting recovery..."
    
    # Get the migration error details
    echo "📋 Migration error details:"
    python manage.py showmigrations employees || true
    
    # Try to fake problematic migrations that might conflict
    echo "🔧 Attempting to resolve migration conflicts..."
    
    # Fake migrations that might have already been applied manually
    python manage.py migrate employees 0002_add_session_tracking_fields --fake || true
    python manage.py migrate employees 0003_add_missing_attendance_fields --fake || true
    
    # Try migration again
    echo "🔄 Retrying migrations after conflict resolution..."
    if python manage.py migrate --noinput; then
        echo "✅ Migrations completed after conflict resolution"
    else
        echo "❌ Migration still failing, checking specific issues..."
        
        # Show current migration state
        python manage.py showmigrations employees
        
        # Try to apply our safe migrations specifically
        echo "🎯 Attempting to apply safe migrations..."
        python manage.py migrate employees 0008_fix_duplicate_column_migration --fake || true
        python manage.py migrate employees 0009_attendance_total_working_hours_and_more --fake || true
        python manage.py migrate employees 0010_reset_migration_state_for_staging || true
        
        # Final attempt
        echo "🔄 Final migration attempt..."
        python manage.py migrate --noinput || {
            echo "💥 All migration attempts failed"
            echo "📋 Final migration state:"
            python manage.py showmigrations employees || true
            echo "🔍 Database schema check:"
            python -c "
import django
import os
from django.db import connection
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()
with connection.cursor() as cursor:
    cursor.execute('SELECT column_name FROM information_schema.columns WHERE table_name=\\'employees_attendance\\' ORDER BY ordinal_position')
    columns = [row[0] for row in cursor.fetchall()]
    print(f'Current columns: {columns}')
" || true
            exit 1
        }
    fi
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
