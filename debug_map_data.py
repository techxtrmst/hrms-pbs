import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Attendance, LocationLog

# Get the most recent attendance with location data
attendance = Attendance.objects.filter(location_in__isnull=False).last()

if not attendance:
    print("No attendance records with location_in found.")
else:
    print(f"Debug for Attendance ID: {attendance.id}")
    print(f"Employee: {attendance.employee.user.get_full_name()}")
    print(f"Clock In: {attendance.clock_in}")
    print(f"Location In: {attendance.location_in}")
    print(f"Clock Out: {attendance.clock_out}")
    print(f"Location Out: {attendance.location_out}")
    
    end_time = attendance.clock_out if attendance.clock_out else timezone.now()
    logs = LocationLog.objects.filter(
        employee=attendance.employee,
        timestamp__gte=attendance.clock_in,
        timestamp__lte=end_time
    ).order_by('timestamp')
    
    print(f"Log Count: {logs.count()}")
    for log in logs[:5]:
        print(f"Log: {log.timestamp} - {log.latitude}, {log.longitude}")
