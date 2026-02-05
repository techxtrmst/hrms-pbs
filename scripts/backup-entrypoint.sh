#!/bin/bash
# =============================================================================
# HRMS-PBS Backup Container Entrypoint
# =============================================================================
# Starts both supercronic (scheduled backups) and trigger watcher (manual backups)
# =============================================================================

set -euo pipefail

echo "Starting HRMS-PBS Backup Container..."

# Start trigger watcher in background
echo "Starting backup trigger watcher..."
/scripts/backup-trigger-watcher.sh &
WATCHER_PID=$!

# Start supercronic in foreground
echo "Starting supercronic scheduler..."
exec supercronic -json /etc/supercronic/backup-crontab
