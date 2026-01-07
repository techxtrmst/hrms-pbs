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
python manage.py migrate --noinput --fake-initial

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
