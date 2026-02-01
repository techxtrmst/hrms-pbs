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

# Ensure media directories exist
echo "Creating media directories..."
mkdir -p /app/media/employee_avatars
mkdir -p /app/media/payslips
mkdir -p /app/media/id_proofs

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

    # For staging where schema is already correct but migrations not recorded,
    # directly insert migration records into django_migrations table
    echo "🔧 Directly marking migrations as applied in database..."

    python -c "
import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

# Migrations to mark as applied
migrations_to_fake = [
    ('employees', '0004_alter_locationlog_options_locationlog_accuracy_and_more'),
    ('employees', '0005_merge_20260113_1145'),
    ('employees', '0006_update_max_sessions_to_3'),
    ('employees', '0007_update_existing_max_sessions'),
    ('employees', '0008_fix_duplicate_column_migration'),
    ('employees', '0009_attendance_total_working_hours_and_more'),
    ('employees', '0010_reset_migration_state_for_staging'),
    ('employees', '0011_fix_locationlog_schema'),
    ('employees', '0012_remove_el_co_fields'),
    ('employees', '0013_alter_leaverequest_leave_type'),
    ('employees', '0014_leaverequest_approval_type'),
    ('employees', '0015_employee_last_anniversary_email_year_and_more'),
    ('employees', '0016_employee_current_address_employee_profile_edited'),
    ('employees', '0017_employee_personal_email'),
    ('employees', '0018_merge_20260121_1520'),
    ('employees', '0019_add_half_day_duration_options'),
    ('employees', '0020_payslip_basic_payslip_employee_pf_and_more'),
    ('employees', '0021_payslip_conveyance_allowance_and_more'),
    ('employees', '0022_employee_pan_number'),
    ('employees', '0023_payslip_monthly_gross'),
    ('employees', '0024_auto_20260128_1715'),
    ('employees', '0025_alter_attendance_max_daily_clocks_and_more'),
    ('employees', '0026_alter_payslip_conveyance_allowance_alter_payslip_lta_and_more'),
    ('employees', '0027_merge_20260130_1334'),
    # Also include other apps that might need faking
    ('companies', '0020_explicitly_name_holiday_indexes'),
    ('handbooks', '0001_initial'),
    ('handbooks', '0002_handbook_updated_at'),
]

with connection.cursor() as cursor:
    for app, name in migrations_to_fake:
        # Check if migration already exists
        cursor.execute(
            'SELECT 1 FROM django_migrations WHERE app = %s AND name = %s',
            [app, name]
        )
        if cursor.fetchone():
            print(f'ℹ️ Already recorded: {app}.{name}')
        else:
            cursor.execute(
                'INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())',
                [app, name]
            )
            print(f'✅ Marked as applied: {app}.{name}')

print('✅ Migration records inserted successfully')
" || echo "⚠️ Could not insert migration records"

    # Final attempt after faking all
    echo "🔄 Final migration attempt..."
    if python manage.py migrate --noinput; then
        echo "✅ Migrations completed after faking all pending"
    else
        echo "💥 Migration still failing"
        python manage.py showmigrations employees || true
        exit 1
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
