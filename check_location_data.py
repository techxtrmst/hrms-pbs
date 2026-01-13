from employees.models import Attendance, LocationLog, Employee
from django.utils import timezone

# Find employees with recent attendance
print("=" * 60)
print("ATTENDANCE DATA CHECK")
print("=" * 60)

recent_attendances = Attendance.objects.order_by('-date')[:5]
for att in recent_attendances:
    print(f"\nAttendance ID: {att.id}")
    print(f"Employee: {att.employee.user.get_full_name()} (ID: {att.employee.id})")
    print(f"Date: {att.date}")
    print(f"Clock In: {att.clock_in}")
    print(f"Clock Out: {att.clock_out}")
    print(f"Location In: {att.location_in}")
    print(f"Location Out: {att.location_out}")
    print(f"Status: {att.status}")
    
    # Check LocationLogs for this attendance
    logs = LocationLog.objects.filter(
        employee=att.employee,
        timestamp__date=att.date
    ).count()
    print(f"LocationLogs for this date: {logs}")
    print("-" * 60)

print("\n" + "=" * 60)
print("LOCATION LOGS")
print("=" * 60)
total_logs = LocationLog.objects.count()
print(f"Total LocationLog records: {total_logs}")

if total_logs > 0:
    recent_logs = LocationLog.objects.order_by('-timestamp')[:10]
    for log in recent_logs:
        print(f"\nLog ID: {log.id}")
        print(f"Employee: {log.employee.user.get_full_name()}")
        print(f"Timestamp: {log.timestamp}")
        print(f"Type: {log.log_type}")
        print(f"Location: {log.latitude}, {log.longitude}")
        print(f"Accuracy: {log.accuracy}m")
