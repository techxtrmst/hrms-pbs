#!/bin/sh
set -e

SERVICE_ROLE="${SERVICE_ROLE:-web}"

echo "==== Starting HRMS Backend (Role: $SERVICE_ROLE) ===="

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
    
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
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

# Only run migrations and collect static for web service
if [ "$SERVICE_ROLE" = "web" ]; then
    echo "Running database migrations..."
    python manage.py migrate --noinput --fake-initial

    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

# Start appropriate service based on role
case "$SERVICE_ROLE" in
    web)
        echo "Starting Gunicorn WSGI server..."
        exec gunicorn hrms_core.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers 4 \
            --timeout 300 \
            --keep-alive 5 \
            --log-level info \
            --access-logfile - \
            --error-logfile -
        ;;
    
    celery_worker)
        echo "Starting Celery worker..."
        exec celery -A hrms_core worker \
            --loglevel=info \
            --concurrency=4 \
            --max-tasks-per-child=1000
        ;;
    
    celery_beat)
        echo "Starting Celery beat scheduler..."
        exec celery -A hrms_core beat \
            --loglevel=info \
            --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    
    *)
        echo "ERROR: Unknown SERVICE_ROLE: $SERVICE_ROLE"
        echo "Valid roles: web, celery_worker, celery_beat"
        exit 1
        ;;
esac
