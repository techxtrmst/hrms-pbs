#!/bin/bash
# =============================================================================
# HRMS-PBS Backup Trigger Watcher
# =============================================================================
# Watches for trigger files and executes backups immediately
# This allows the Django admin to trigger backups without docker socket access
# =============================================================================

set -euo pipefail

TRIGGER_DIR="/var/run/backup-triggers"
LOG_PREFIX="[TRIGGER-WATCHER]"

# Create trigger directory if it doesn't exist
mkdir -p "$TRIGGER_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX Watching for backup triggers in $TRIGGER_DIR"

# Watch for trigger files
while true; do
    # Check for database backup trigger
    if [ -f "$TRIGGER_DIR/trigger-database" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX Database backup triggered"
        rm -f "$TRIGGER_DIR/trigger-database"
        /scripts/backup-database.sh >> /var/log/backup/database.log 2>&1 &
    fi

    # Check for media backup trigger
    if [ -f "$TRIGGER_DIR/trigger-media" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX Media backup triggered"
        rm -f "$TRIGGER_DIR/trigger-media"
        /scripts/backup-media.sh >> /var/log/backup/media.log 2>&1 &
    fi

    # Check for restore test trigger
    if [ -f "$TRIGGER_DIR/trigger-restore" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX Restore test triggered"
        rm -f "$TRIGGER_DIR/trigger-restore"
        /scripts/restore-test.sh >> /var/log/backup/restore-test.log 2>&1 &
    fi

    # Sleep for 5 seconds before checking again
    sleep 5
done
