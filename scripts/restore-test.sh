#!/bin/bash
# =============================================================================
# HRMS-PBS Monthly Restore Test Script
# =============================================================================
# Validates backup integrity by restoring to a temporary database
# Runs monthly on the 1st at 03:00
#
# Features:
# - Restores latest database snapshot to temp container
# - Validates data integrity with basic queries
# - Reports results to MS Teams
# - Cleans up temp resources after test
# =============================================================================

set -euo pipefail

# Configuration
REST IC_REPO="rclone:gdrive:HRMS-Backups/database"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_PREFIX="[RESTORE-TEST]"
TEMP_DIR="/tmp/restore-test-${TIMESTAMP}"

# Database connection for temp restore
PGHOST="${PGHOST:-db}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"

# Teams webhook for notifications
TEAMS_WEBHOOK_URL="${STAGING_TEAMS_WEBHOOK_URL:-}"

# Test results
TEST_PASSED=true
TEST_RESULTS=""

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

add_test_result() {
    local test_name="$1"
    local passed="$2"
    local details="$3"

    local status_icon="✅"
    if [ "$passed" = "false" ]; then
        status_icon="❌"
        TEST_PASSED=false
    fi

    TEST_RESULTS="${TEST_RESULTS}\n${status_icon} ${test_name}: ${details}"
    log_info "Test '${test_name}': $([ "$passed" = "true" ] && echo 'PASSED' || echo 'FAILED') - ${details}"
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

    # Escape newlines for JSON
    local escaped_results=$(echo -e "$TEST_RESULTS" | sed 's/$/\\n/' | tr -d '\n')

    local payload=$(cat <<EOF
{
    "@type": "MessageCard",
    "@context": "http://schema.org/extensions",
    "themeColor": "${color}",
    "summary": "HRMS Restore Test ${status_display}",
    "sections": [{
        "activityTitle": "${emoji} HRMS Monthly Restore Test - ${status_display}",
        "facts": [
            {"name": "Timestamp", "value": "${TIMESTAMP}"},
            {"name": "Repository", "value": "GoogleDrive/HRMS-Backups/database"}
        ],
        "text": "${message}\n\n**Test Results:**${escaped_results}"
    }]
}
EOF
)

    curl -sS -X POST -H "Content-Type: application/json" -d "$payload" "$TEAMS_WEBHOOK_URL" > /dev/null 2>&1 || true
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary resources..."

    # Drop test database if it exists
    PGPASSWORD="${PGPASSWORD:-postgres}" psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -c "DROP DATABASE IF EXISTS hrms_restore_test;" 2>/dev/null || true

    # Remove temp directory
    rm -rf "$TEMP_DIR" 2>/dev/null || true

    log_info "Cleanup completed"
}

# Ensure cleanup runs on exit
trap cleanup EXIT

# =============================================================================
# Pre-flight Checks
# =============================================================================

log_info "Starting monthly restore test..."
log_info "Timestamp: $TIMESTAMP"

# Generate rclone config from template if needed
if [ -f /scripts/rclone.conf.template ] && [ ! -f /root/.config/rclone/rclone.conf ]; then
    log_info "Generating rclone configuration..."
    mkdir -p /root/.config/rclone
    envsubst < /scripts/rclone.conf.template > /root/.config/rclone/rclone.conf
fi

# Check database connectivity
log_info "Checking database connectivity..."
if ! pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -q; then
    log_error "Database is not ready!"
    add_test_result "Database Connectivity" "false" "Cannot connect to ${PGHOST}:${PGPORT}"
    send_teams_notification "failure" "Restore test aborted - database not accessible" "FF0000"
    exit 1
fi
add_test_result "Database Connectivity" "true" "Connected to ${PGHOST}:${PGPORT}"

# Check if restic repository exists
RESTIC_OPTS=$(get_restic_opts)
if ! restic $RESTIC_OPTS -r "$RESTIC_REPO" snapshots > /dev/null 2>&1; then
    log_error "Restic repository not accessible!"
    add_test_result "Repository Access" "false" "Cannot access Google Drive backup repository"
    send_teams_notification "failure" "Restore test aborted - backup repository not accessible" "FF0000"
    exit 1
fi
add_test_result "Repository Access" "true" "Google Drive repository accessible"

# =============================================================================
# Get Latest Snapshot Info
# =============================================================================

log_info "Finding latest database snapshot..."

LATEST_SNAPSHOT=$(restic $RESTIC_OPTS -r "$RESTIC_REPO" snapshots --tag "database" --latest 1 --json 2>/dev/null | grep -o '"short_id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")

if [ -z "$LATEST_SNAPSHOT" ]; then
    log_error "No database snapshots found!"
    add_test_result "Snapshot Availability" "false" "No database snapshots in repository"
    send_teams_notification "failure" "Restore test aborted - no snapshots found" "FF0000"
    exit 1
fi

SNAPSHOT_TIME=$(restic $RESTIC_OPTS -r "$RESTIC_REPO" snapshots --tag "database" --latest 1 --json 2>/dev/null | grep -o '"time":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")

add_test_result "Snapshot Availability" "true" "Latest: ${LATEST_SNAPSHOT} (${SNAPSHOT_TIME})"
log_info "Latest snapshot: $LATEST_SNAPSHOT from $SNAPSHOT_TIME"

# =============================================================================
# Restore Backup to Temp Location
# =============================================================================

log_info "Restoring snapshot to temporary location..."
mkdir -p "$TEMP_DIR"

RESTORE_START=$(date +%s)

if restic $RESTIC_OPTS -r "$RESTIC_REPO" restore "$LATEST_SNAPSHOT" --target "$TEMP_DIR" 2>&1; then
    RESTORE_END=$(date +%s)
    RESTORE_DURATION=$((RESTORE_END - RESTORE_START))
    add_test_result "Snapshot Restore" "true" "Restored in ${RESTORE_DURATION}s"
    log_success "Snapshot restored in ${RESTORE_DURATION} seconds"
else
    add_test_result "Snapshot Restore" "false" "Failed to restore snapshot"
    send_teams_notification "failure" "Restore test failed - could not restore snapshot" "FF0000"
    exit 1
fi

# Find the restored dump file
DUMP_FILE=$(find "$TEMP_DIR" -name "*.dump" -type f 2>/dev/null | head -1)

if [ -z "$DUMP_FILE" ]; then
    log_error "No dump file found in restored data!"
    add_test_result "Dump File Check" "false" "No .dump file in restored data"
    send_teams_notification "failure" "Restore test failed - no dump file found" "FF0000"
    exit 1
fi

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
add_test_result "Dump File Check" "true" "Found: $(basename "$DUMP_FILE") (${DUMP_SIZE})"
log_info "Found dump file: $DUMP_FILE ($DUMP_SIZE)"

# =============================================================================
# Restore to Test Database
# =============================================================================

log_info "Creating test database..."

# Create test database
export PGPASSWORD="${PGPASSWORD:-postgres}"

if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -c "CREATE DATABASE hrms_restore_test;" 2>&1; then
    add_test_result "Test DB Creation" "true" "Created hrms_restore_test database"
else
    add_test_result "Test DB Creation" "false" "Failed to create test database"
    send_teams_notification "failure" "Restore test failed - could not create test database" "FF0000"
    exit 1
fi

log_info "Restoring dump to test database..."

if pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d hrms_restore_test --no-owner --no-acl "$DUMP_FILE" 2>&1; then
    add_test_result "Database Restore" "true" "pg_restore completed successfully"
    log_success "Database restored successfully"
else
    # pg_restore may return non-zero for warnings, check if data exists
    TABLE_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d hrms_restore_test -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$TABLE_COUNT" -gt "0" ]; then
        add_test_result "Database Restore" "true" "pg_restore completed with warnings (${TABLE_COUNT} tables)"
        log_info "Database restored with warnings ($TABLE_COUNT tables)"
    else
        add_test_result "Database Restore" "false" "pg_restore failed - no tables created"
        send_teams_notification "failure" "Restore test failed - database restore failed" "FF0000"
        exit 1
    fi
fi

# =============================================================================
# Validate Restored Data
# =============================================================================

log_info "Validating restored data..."

# Check table count
TABLE_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d hrms_restore_test -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$TABLE_COUNT" -gt "10" ]; then
    add_test_result "Table Count" "true" "${TABLE_COUNT} tables found"
else
    add_test_result "Table Count" "false" "Only ${TABLE_COUNT} tables (expected >10)"
fi

# Check for key tables (Django + HRMS specific)
KEY_TABLES=("django_migrations" "auth_user" "employees_employee" "companies_company")
MISSING_TABLES=""

for table in "${KEY_TABLES[@]}"; do
    EXISTS=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d hrms_restore_test -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '${table}');" 2>/dev/null | tr -d ' ' || echo "f")
    if [ "$EXISTS" != "t" ]; then
        MISSING_TABLES="${MISSING_TABLES} ${table}"
    fi
done

if [ -z "$MISSING_TABLES" ]; then
    add_test_result "Key Tables" "true" "All key tables present"
else
    add_test_result "Key Tables" "false" "Missing:${MISSING_TABLES}"
fi

# Check for data in key tables
USER_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d hrms_restore_test -t -c "SELECT COUNT(*) FROM auth_user;" 2>/dev/null | tr -d ' ' || echo "0")
EMPLOYEE_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d hrms_restore_test -t -c "SELECT COUNT(*) FROM employees_employee;" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$USER_COUNT" -gt "0" ]; then
    add_test_result "User Data" "true" "${USER_COUNT} users found"
else
    add_test_result "User Data" "false" "No users in restored database"
fi

if [ "$EMPLOYEE_COUNT" -gt "0" ]; then
    add_test_result "Employee Data" "true" "${EMPLOYEE_COUNT} employees found"
else
    add_test_result "Employee Data" "false" "No employees in restored database"
fi

# =============================================================================
# Summary and Notification
# =============================================================================

log_info "Restore test completed"
echo ""
echo "============================================="
echo "RESTORE TEST SUMMARY"
echo "============================================="
echo -e "$TEST_RESULTS"
echo "============================================="

if [ "$TEST_PASSED" = "true" ]; then
    log_success "All restore tests PASSED!"
    send_teams_notification "success" "Monthly restore verification completed successfully. All integrity checks passed." "00FF00"
else
    log_error "Some restore tests FAILED!"
    send_teams_notification "failure" "Monthly restore verification completed with failures. Review test results." "FF0000"
    exit 1
fi
