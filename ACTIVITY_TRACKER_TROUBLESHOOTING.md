# Activity Tracker Troubleshooting Guide

## Problem: Device Shows "Never Synced"

When an employee downloads and runs the setup file but the admin panel shows "Never Synced", follow these steps:

---

## Step 1: Verify Static Files are Accessible

### Test the EXE Download URL

Open this URL in your browser (replace with your domain):
```
https://your-production-domain.com/static/activity_monitoring/bin/ActivityTracker.exe
```

**Expected Result:** The file should download (33MB)

**If 404 Error:**
1. SSH into your production server
2. Run: `python manage.py collectstatic --noinput`
3. Verify file exists: `ls -lh /app/staticfiles/activity_monitoring/bin/ActivityTracker.exe`
4. Restart nginx: `docker-compose restart nginx` or `systemctl restart nginx`

---

## Step 2: Check Employee's Setup Process

### What the Employee Should Do:

1. **Download Setup File:**
   - Go to their profile page
   - Click "Download Activity Tracker"
   - Save `setup_tracker.bat` file

2. **Run Setup File:**
   - Right-click `setup_tracker.bat`
   - Select "Run as Administrator" (important!)
   - Wait for download to complete
   - Should see: "✅ TRACKER IS NOW ACTIVE"

3. **Verify Installation:**
   - Press `Win + R`
   - Type: `%LOCALAPPDATA%\PetaBytz-Tracker`
   - Should see:
     - `ActivityTracker.exe` (33MB)
     - `config.json` (contains their token)

4. **Check if Running:**
   - Press `Ctrl + Shift + Esc` (Task Manager)
   - Look for "ActivityTracker.exe" in Processes
   - Should be running in background

---

## Step 3: Manual Troubleshooting

### If Setup Fails:

**Check 1: Internet Connection**
```bash
# Employee should test:
curl -I https://your-domain.com/static/activity_monitoring/bin/ActivityTracker.exe
```

**Check 2: Firewall/Antivirus**
- Windows Defender might block the download
- Corporate firewall might block the EXE
- Add exception for: `%LOCALAPPDATA%\PetaBytz-Tracker\`

**Check 3: Manual Installation**
```batch
# Employee can manually download and place files:
1. Download EXE from: https://your-domain.com/static/activity_monitoring/bin/ActivityTracker.exe
2. Create folder: %LOCALAPPDATA%\PetaBytz-Tracker
3. Copy EXE to that folder
4. Create config.json with their token (get from admin)
5. Run ActivityTracker.exe
```

---

## Step 4: Verify Server is Receiving Data

### Check Django Logs:

```bash
# SSH into production server
docker-compose logs -f backend | grep "Sync Success"
```

**Expected Output:**
```
Sync Success for John Doe at 2026-03-13 10:30:15
```

### Check Database:

```python
# Django shell
python manage.py shell

from activity_monitoring.models import EmployeeDevice, ActivityPulse
from employees.models import Employee

# Check device
employee = Employee.objects.get(user__email="employee@example.com")
device = EmployeeDevice.objects.filter(employee=employee).first()
print(f"Device: {device}")
print(f"Token: {device.token}")
print(f"Last Seen: {device.last_seen}")
print(f"Is Active: {device.is_active}")

# Check recent activity
pulses = ActivityPulse.objects.filter(employee=employee).order_by('-timestamp')[:5]
for pulse in pulses:
    print(f"{pulse.timestamp}: Idle={pulse.is_idle}")
```

---

## Step 5: Common Issues & Solutions

### Issue 1: "curl: command not found" in BAT file

**Solution:** The setup uses `curl` which is built into Windows 10+. If missing:
- Update Windows to latest version
- Or manually download the EXE (see Check 3 above)

### Issue 2: "Access Denied" when running setup

**Solution:** 
- Right-click setup file → "Run as Administrator"
- Or disable UAC temporarily

### Issue 3: Tracker stops after restart

**Solution:**
- Check Windows startup registry:
  ```
  Win + R → regedit
  Navigate to: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
  Look for: PetaBytz-Tracker
  ```
- If missing, re-run setup file

### Issue 4: "Invalid or inactive token"

**Solution:**
- Admin should check: Activity Monitoring → Employee Devices
- Ensure device is marked as "Active"
- If needed, delete old device and have employee re-download setup

### Issue 5: Data not showing in dashboard

**Solution:**
- Wait 60 seconds (tracker syncs every minute)
- Check if employee is actually using the computer
- Verify tracker is running (Task Manager)
- Check server logs for sync errors

---

## Step 6: Testing the Sync Endpoint

### Test API Endpoint:

```bash
# Get employee's token from admin panel
TOKEN="their-device-token-here"

# Test sync endpoint
curl -X POST https://your-domain.com/activity-tracking/api/sync/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "app_activities": [],
    "browser_activities": [],
    "system_events": [],
    "is_idle": false,
    "idle_seconds": 0
  }'
```

**Expected Response:**
```json
{"status": "success"}
```

---

## Architecture Overview

```
Employee Computer                    Production Server
─────────────────                    ─────────────────

1. Download setup.bat  ──────────>  Django serves BAT file
                                     (with personalized token)

2. BAT downloads EXE   ──────────>  Nginx serves static file
                                     /static/.../ActivityTracker.exe

3. Tracker runs        ──────────>  Sends data every 60s
   - Monitors windows               POST /activity-tracking/api/sync/
   - Tracks browser                 Authorization: Token XXX
   - Detects USB

4. Server stores data  <──────────  Django REST API
                                     - Creates ActivitySession
                                     - Stores AppActivity
                                     - Stores BrowserActivity
                                     - Updates ActivityPulse

5. Admin views data    ──────────>  Dashboard shows:
                                     - Online/Offline status
                                     - Last sync time
                                     - Activity breakdown
```

---

## Quick Diagnosis Checklist

- [ ] EXE file accessible at `/static/activity_monitoring/bin/ActivityTracker.exe`
- [ ] Employee ran setup as Administrator
- [ ] Tracker installed to `%LOCALAPPDATA%\PetaBytz-Tracker\`
- [ ] `ActivityTracker.exe` is running in Task Manager
- [ ] `config.json` contains valid token
- [ ] Firewall/antivirus not blocking
- [ ] Server logs show "Sync Success" messages
- [ ] Device marked as "Active" in admin
- [ ] Last seen timestamp is recent (< 2 minutes ago)

---

## Support Commands

### For Admin:

```python
# Check all devices and their status
from activity_monitoring.models import EmployeeDevice
from django.utils import timezone
from datetime import timedelta

recent = timezone.now() - timedelta(minutes=5)
online = EmployeeDevice.objects.filter(last_seen__gte=recent, is_active=True)
print(f"Online devices: {online.count()}")

for device in online:
    print(f"- {device.employee.user.get_full_name()}: {device.last_seen}")
```

### For Employee:

```batch
REM Check if tracker is installed
dir "%LOCALAPPDATA%\PetaBytz-Tracker"

REM Check if tracker is running
tasklist | findstr ActivityTracker

REM View config
type "%LOCALAPPDATA%\PetaBytz-Tracker\config.json"

REM Restart tracker
taskkill /F /IM ActivityTracker.exe
start "" "%LOCALAPPDATA%\PetaBytz-Tracker\ActivityTracker.exe"
```

---

## Need More Help?

1. Check server logs: `docker-compose logs -f backend`
2. Check nginx logs: `docker-compose logs -f nginx`
3. Enable debug logging in tracker (edit config.json)
4. Contact system administrator with:
   - Employee name
   - Device token
   - Screenshot of Task Manager
   - Screenshot of tracker folder
