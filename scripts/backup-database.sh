#!/bin/bash
# =============================================================================
# HRMS-PBS Database Backup Script
# =============================================================================
# Backs up PostgreSQL database to Google Drive using restic + rclone
# Runs every 3 hours (00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00)
#
# Features:
# - Deduplication via restic (saves ~70% storage)
# - Optional encryption (enabled if RESTIC_PASSWORD is set)
# - GFS retention policy (8 latest, 7 daily, 4 weekly, 12 monthly)
# - MS Teams notifications on success/failure
# =============================================================================

set -euo pipefail

# Configuration
BACKUP_TYPE="database"
RESTIC_REPO="rclone:gdrive:HRMS-Backups/database"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_PREFIX="[DB-BACKUP]"

# Database connection (uses Docker network)
PGHOST="${PGHOST:-db}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-postgres}"

# Teams webhook for notifications
TEAMS_WEBHOOK_URL="${STAGING_TEAMS_WEBHOOK_URL:-}"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} INFO: $1"
}

log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} ERROR: $1" >&2
}

log_success() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} SUCCESS: $1"
}

# Build restic options for optional encryption
get_restic_opts() {
    if [ -n "${RESTIC_PASSWORD:-}" ]; then
        echo ""
    else
        echo "--insecure-no-password"
    fi
}

# Send Teams notification
send_teams_notification() {
    local status="$1"
    local message="$2"
    local color="$3"

    if [ -z "$TEAMS_WEBHOOK_URL" ]; then
        log_info "Teams webhook not configured, skipping notification"
        return 0
    fi

    local emoji="✅"
    local status_display="Success"
    if [ "$status" = "failure" ]; then
        emoji="❌"
        status_display="Failed"
    elif [ "$status" = "warning" ]; then
        emoji="⚠️"
        status_display="Warning"
    fi

    local payload=$(cat <<EOF
{
    "@type": "MessageCard",
    "@context": "http://schema.org/extensions",
    "themeColor": "${color}",
    "summary": "HRMS Backup ${status_display}",
    "sections": [{
        "activityTitle": "${emoji} HRMS Database Backup - ${status_display}",
        "facts": [
            {"name": "Timestamp", "value": "${TIMESTAMP}"},
            {"name": "Type", "value": "${BACKUP_TYPE}"},
            {"name": "Repository", "value": "GoogleDrive/HRMS-Backups/database"},
            {"name": "Encryption", "value": "$([ -n "${RESTIC_PASSWORD:-}" ] && echo 'Enabled' || echo 'Disabled')"}
        ],
        "text": "${message}"
    }]
}
EOF
)

    curl -sS -X POST -H "Content-Type: application/json" -d "$payload" "$TEAMS_WEBHOOK_URL" > /dev/null 2>&1 || true
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

log_info "Starting database backup..."
log_info "Timestamp: $TIMESTAMP"
log_info "Encryption: $([ -n "${RESTIC_PASSWORD:-}" ] && echo 'Enabled' || echo 'Disabled')"

# Generate rclone config from template if needed
if [ -f /scripts/rclone.conf.template ] && [ ! -f /root/.config/rclone/rclone.conf ]; then
    log_info "Generating rclone configuration..."
    mkdir -p /root/.config/rclone
    envsubst < /scripts/rclone.conf.template > /root/.config/rclone/rclone.conf
fi

# Verify rclone config exists
if [ ! -f /root/.config/rclone/rclone.conf ]; then
    log_error "rclone configuration not found!"
    send_teams_notification "failure" "rclone configuration not found. Please run init script." "FF0000"
    exit 1
fi

# Check database connectivity
log_info "Checking database connectivity..."
if ! pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -q; then
    log_error "Database is not ready!"
    send_teams_notification "failure" "Database connection failed. Host: ${PGHOST}:${PGPORT}" "FF0000"
    exit 1
fi

log_info "Database connection OK"

# Check if restic repository exists
RESTIC_OPTS=$(get_restic_opts)
log_info "Checking restic repository..."
if ! restic $RESTIC_OPTS -r "$RESTIC_REPO" snapshots > /dev/null 2>&1; then
    log_error "Restic repository not initialized! Run init-backup-repo.sh first."
    send_teams_notification "failure" "Restic repository not initialized. Run: docker compose exec backup /scripts/init-backup-repo.sh" "FF0000"
    exit 1
fi

# =============================================================================
# Perform Backup
# =============================================================================

log_info "Starting pg_dump..."
BACKUP_START=$(date +%s)

# Create backup using pg_dump piped directly to restic
# This avoids writing to disk and streams directly to cloud
if pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" --format=custom --compress=6 | \
    restic $RESTIC_OPTS -r "$RESTIC_REPO" backup --stdin --stdin-filename "hrms_${TIMESTAMP}.dump" --tag "database" --tag "postgresql" --tag "3hourly"; then

    BACKUP_END=$(date +%s)
    BACKUP_DURATION=$((BACKUP_END - BACKUP_START))

    log_success "Database backup completed in ${BACKUP_DURATION} seconds"
else
    log_error "Backup failed!"
    send_teams_notification "failure" "pg_dump or restic backup failed. Check container logs." "FF0000"
    exit 1
fi

# =============================================================================
# Apply Retention Policy
# =============================================================================

log_info "Applying retention policy..."
log_info "Policy: keep-last=8, keep-daily=7, keep-weekly=4, keep-monthly=12"

if restic $RESTIC_OPTS -r "$RESTIC_REPO" forget \
    --keep-last 8 \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 12 \
    --tag "database" \
    --prune; then
    log_success "Retention policy applied"
else
    log_error "Retention policy failed (backup still succeeded)"
    send_teams_notification "warning" "Backup succeeded but retention policy failed. Manual cleanup may be needed." "FFA500"
fi

# =============================================================================
# Get Backup Statistics
# =============================================================================

log_info "Gathering backup statistics..."

# Get latest snapshot info
SNAPSHOT_INFO=$(restic $RESTIC_OPTS -r "$RESTIC_REPO" snapshots --latest 1 --json 2>/dev/null | head -1 || echo "[]")
SNAPSHOT_COUNT=$(restic $RESTIC_OPTS -r "$RESTIC_REPO" snapshots --tag "database" --json 2>/dev/null | grep -c '"id"' || echo "0")

# Get repository stats
REPO_STATS=$(restic $RESTIC_OPTS -r "$RESTIC_REPO" stats --json 2>/dev/null || echo '{"total_size": 0}')
REPO_SIZE=$(echo "$REPO_STATS" | grep -o '"total_size":[0-9]*' | cut -d: -f2 || echo "0")
REPO_SIZE_MB=$((REPO_SIZE / 1024 / 1024))

log_info "Total snapshots: $SNAPSHOT_COUNT"
log_info "Repository size: ${REPO_SIZE_MB}MB"

# =============================================================================
# Send Success Notification
# =============================================================================

send_teams_notification "success" "Backup completed in ${BACKUP_DURATION}s. Total snapshots: ${SNAPSHOT_COUNT}. Repo size: ${REPO_SIZE_MB}MB" "00FF00"

log_success "Database backup completed successfully!"
log_info "Duration: ${BACKUP_DURATION}s | Snapshots: ${SNAPSHOT_COUNT} | Size: ${REPO_SIZE_MB}MB"
