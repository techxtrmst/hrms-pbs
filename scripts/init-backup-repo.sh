#!/bin/bash
# =============================================================================
# HRMS-PBS Backup Repository Initialization Script
# =============================================================================
# One-time setup script to initialize restic repositories in Google Drive
# Run manually after first deployment:
#   docker compose exec backup /scripts/init-backup-repo.sh
#
# Features:
# - Initializes database and media backup repositories
# - Configures encryption based on RESTIC_PASSWORD presence
# - Generates rclone config from template
# - Tests Google Drive connectivity
# =============================================================================

set -euo pipefail

LOG_PREFIX="[INIT-BACKUP]"

# Repository paths
DB_REPO="rclone:gdrive:HRMS-Backups/database"
MEDIA_REPO="rclone:gdrive:HRMS-Backups/media"

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

log_warning() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} WARNING: $1"
}

# Build restic arguments for optional encryption
get_restic_opts() {
    if [ -n "${RESTIC_PASSWORD:-}" ]; then
        echo ""
    else
        echo "--insecure-no-password"
    fi
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

echo ""
echo "============================================="
echo "  HRMS-PBS Backup Repository Initialization"
echo "============================================="
echo ""

log_info "Checking prerequisites..."

# Check for required environment variable - only GDRIVE_TOKEN is strictly required
if [ -z "${GDRIVE_TOKEN:-}" ]; then
    log_error "Missing required environment variable: GDRIVE_TOKEN"
    echo ""
    echo "Please ensure the following is set in your environment:"
    echo "  - GDRIVE_TOKEN (obtain via rclone-authorize.ps1)"
    echo ""
    exit 1
fi

# Encryption mode
if [ -n "${RESTIC_PASSWORD:-}" ]; then
    log_info "Encryption: ENABLED (RESTIC_PASSWORD is set)"
    ENCRYPTION_MODE="encrypted"
else
    log_info "Encryption: DISABLED (RESTIC_PASSWORD not set)"
    ENCRYPTION_MODE="unencrypted"
fi

# =============================================================================
# Generate rclone Configuration
# =============================================================================

log_info "Generating rclone configuration..."

mkdir -p /root/.config/rclone

if [ -f /scripts/rclone.conf.template ]; then
    envsubst < /scripts/rclone.conf.template > /root/.config/rclone/rclone.conf
    log_success "rclone configuration generated"
else
    log_error "rclone.conf.template not found!"
    exit 1
fi

# =============================================================================
# Test Google Drive Connectivity
# =============================================================================

log_info "Testing Google Drive connectivity..."

if rclone lsd gdrive: > /dev/null 2>&1; then
    log_success "Google Drive connection successful"
else
    log_error "Google Drive connection failed!"
    echo ""
    echo "Possible causes:"
    echo "  1. GDRIVE_TOKEN is invalid or expired"
    echo "  2. Network connectivity issues"
    echo "  3. Google Drive permissions not granted"
    echo ""
    echo "To obtain a new token, run rclone-authorize.ps1 on a machine with a browser"
    echo ""
    exit 1
fi

# Create backup folders if they don't exist
log_info "Creating Google Drive backup folders..."
rclone mkdir gdrive:HRMS-Backups/database 2>/dev/null || true
rclone mkdir gdrive:HRMS-Backups/media 2>/dev/null || true
log_success "Google Drive folders ready"

# =============================================================================
# Initialize Database Repository
# =============================================================================

RESTIC_OPTS=$(get_restic_opts)

log_info "Checking database backup repository..."

if restic $RESTIC_OPTS -r "$DB_REPO" snapshots > /dev/null 2>&1; then
    log_warning "Database repository already initialized"
    SNAPSHOT_COUNT=$(restic $RESTIC_OPTS -r "$DB_REPO" snapshots --json 2>/dev/null | grep -c '"id"' || echo "0")
    log_info "Existing snapshots: $SNAPSHOT_COUNT"
else
    log_info "Initializing database backup repository..."

    if restic $RESTIC_OPTS -r "$DB_REPO" init --repository-version 2; then
        log_success "Database repository initialized (${ENCRYPTION_MODE})"
    else
        log_error "Failed to initialize database repository!"
        exit 1
    fi
fi

# =============================================================================
# Initialize Media Repository
# =============================================================================

log_info "Checking media backup repository..."

if restic $RESTIC_OPTS -r "$MEDIA_REPO" snapshots > /dev/null 2>&1; then
    log_warning "Media repository already initialized"
    SNAPSHOT_COUNT=$(restic $RESTIC_OPTS -r "$MEDIA_REPO" snapshots --json 2>/dev/null | grep -c '"id"' || echo "0")
    log_info "Existing snapshots: $SNAPSHOT_COUNT"
else
    log_info "Initializing media backup repository..."

    if restic $RESTIC_OPTS -r "$MEDIA_REPO" init --repository-version 2; then
        log_success "Media repository initialized (${ENCRYPTION_MODE})"
    else
        log_error "Failed to initialize media repository!"
        exit 1
    fi
fi

# =============================================================================
# Verify Setup
# =============================================================================

log_info "Verifying backup setup..."

echo ""
echo "============================================="
echo "  Backup Repository Status"
echo "============================================="
echo ""
echo "Database Repository: $DB_REPO"
echo "  Status: $(restic $RESTIC_OPTS -r "$DB_REPO" snapshots > /dev/null 2>&1 && echo '✅ Ready' || echo '❌ Error')"
echo ""
echo "Media Repository: $MEDIA_REPO"
echo "  Status: $(restic $RESTIC_OPTS -r "$MEDIA_REPO" snapshots > /dev/null 2>&1 && echo '✅ Ready' || echo '❌ Error')"
echo ""
echo "Encryption: $([ -n "${RESTIC_PASSWORD:-}" ] && echo '🔒 Enabled' || echo '🔓 Disabled')"
echo ""
echo "============================================="
echo ""

log_success "Backup repository initialization complete!"
echo ""
echo "Next steps:"
echo "  1. Backups will run automatically per schedule:"
echo "     - Database: Every 3 hours (00:00, 03:00, 06:00, ...)"
echo "     - Media: Daily at 02:00"
echo "     - Restore test: Monthly on 1st at 03:00"
echo ""
echo "  2. To run a manual backup now:"
echo "     docker compose exec backup /scripts/backup-database.sh"
echo "     docker compose exec backup /scripts/backup-media.sh"
echo ""
echo "  3. To list existing backups:"
echo "     docker compose exec backup restic -r $DB_REPO snapshots"
echo ""
