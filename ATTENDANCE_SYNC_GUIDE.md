# Attendance Sync Guide

## Overview
This guide explains how to sync attendance records after deployment to ensure all leaves, holidays, and absents are properly reflected in the admin reports.

## Problem
The attendance report was not showing:
- ✗ Approved leaves
- ✗ Holidays
- ✗ Absent days

## Solution
We've created management commands to sync all attendance records from the database.

---

## Commands Available

### 1. `sync_all_attendance` (Recommended - All-in-One)
This command runs all sync operations in the correct order.

```bash
# Sync current year
python manage.py sync_all_attendance

# Sync specific month
python manage.py sync_all_attendance --year 2026 --month 1

# Sync multiple years
python manage.py sync_all_attendance --start-year 2024 --end-year 2026
```

### 2. `sync_leave_holiday_attendance` (Individual - Leaves & Holidays)
Syncs approved leaves and holidays to attendance records.

```bash
# Sync current year
python manage.py sync_leave_holiday_attendance

# Sync specific month
python manage.py sync_leave_holiday_attendance --year 2026 --month 1
```

### 3. `mark_absents` (Individual - Absents)
Marks employees as absent for working days where they didn't clock in.

```bash
# Dry run (preview without making changes)
python manage.py mark_absents --year 2026 --month 1 --dry-run

# Actually mark absents
python manage.py mark_absents --year 2026 --month 1
```

---

## Deployment Workflow

### After Deploying to Staging

1. **SSH into staging server**
   ```bash
   ssh your-staging-server
   cd /path/to/hrms-pbs
   ```

2. **Activate virtual environment** (if using one)
   ```bash
   source venv/bin/activate
   ```

3. **Run the sync command**
   ```bash
   # For current year
   python manage.py sync_all_attendance
   
   # Or for specific year/month
   python manage.py sync_all_attendance --year 2026 --month 1
   ```

4. **Verify in admin reports**
   - Go to Admin Dashboard → Reports
   - Check that leaves, holidays, and absents are now visible
   - Verify the counts match the database records

### For Docker Deployments

```bash
# Enter the container
docker exec -it hrms-container bash

# Run the sync
python manage.py sync_all_attendance --year 2026

# Exit container
exit
```

---

## What Each Command Does

### `sync_leave_holiday_attendance`
- ✓ Creates attendance records with status="LEAVE" for all approved leave requests
- ✓ Creates attendance records with status="HOLIDAY" for all company holidays
- ✓ Skips weekly offs
- ✓ Only processes past dates (not future)

### `mark_absents`
- ✓ Marks employees as absent for working days where:
  - No attendance record exists
  - Not a weekly off
  - Not a holiday
  - Employee had already joined the company
- ✓ Only processes up to yesterday (not today, as employees might still clock in)

---

## Code Changes Made

### 1. Updated `employees/models.py`
Modified `LeaveRequest.approve_leave()` method to automatically create attendance records when leaves are approved.

```python
# Now creates attendance records for each day of approved leave
Attendance.objects.update_or_create(
    employee=self.employee,
    date=current_date,
    defaults={
        'status': 'LEAVE',
        'clock_in': None,
        'clock_out': None,
    }
)
```

### 2. Created Management Commands
- `sync_leave_holiday_attendance.py` - Backfill existing approved leaves and holidays
- `mark_absents.py` - Mark absent days for all employees
- `sync_all_attendance.py` - Run all sync operations together

---

## Testing Locally

Before deploying, test locally:

```bash
# Test with dry run
python manage.py mark_absents --year 2026 --month 1 --dry-run

# Run actual sync
python manage.py sync_all_attendance --year 2026 --month 1

# Check the results in admin reports
python manage.py runserver
# Visit: http://localhost:8000/analytics/report/
```

---

## Troubleshooting

### Issue: No records created
**Check:**
- Are there approved leaves in the database?
- Are there holidays configured?
- Are employees marked as active?

**Verify:**
```bash
python manage.py shell
>>> from employees.models import LeaveRequest
>>> from companies.models import Holiday
>>> LeaveRequest.objects.filter(status='APPROVED').count()
>>> Holiday.objects.filter(is_active=True).count()
```

### Issue: Absents not showing
**Check:**
- Did you run `mark_absents` command?
- Are you checking dates in the past (not today or future)?
- Are weekly offs configured correctly?

### Issue: Holidays not showing
**Check:**
- Are holidays created in the database?
- Do holidays have the correct location assigned?
- Are employees assigned to the same location as holidays?

---

## Automation (Optional)

To automatically sync attendance daily, add a cron job:

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 1 AM
0 1 * * * cd /path/to/hrms-pbs && python manage.py mark_absents --year $(date +\%Y) >> /var/log/attendance_sync.log 2>&1
```

---

## Summary

✅ **Before deployment:** Code changes are committed
✅ **After deployment:** Run `python manage.py sync_all_attendance`
✅ **Result:** All leaves, holidays, and absents show correctly in reports

---

## Questions?

If you encounter any issues, check:
1. Database has the required data (leaves, holidays)
2. Employees are marked as active
3. Locations are properly configured
4. Weekly offs are set correctly for employees
