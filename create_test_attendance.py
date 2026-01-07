#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, Attendance
from django.utils import timezone
import pytz

def create_test_attendance():
    print("🔧 CREATING TEST ATTENDANCE RECORD")
    print("=" * 50)
    
    # Get test employee
    employee = Employee.objects.get(user__email='softtest@example.com')
    today = timezone.localdate()
    
    # Check if attendance exists
    attendance = Attendance.objects.filter(employee=employee, date=today).first()
    if attendance:
        print(f"✅ Attendance exists: {attendance.clock_in}")
    else:
        print("📝 No attendance found, creating test record...")
        # Create test attendance with current time
        attendance = Attendance.objects.create(
            employee=employee,
            date=today,
            clock_in=timezone.now(),
            status='PRESENT'
        )
        print(f"✅ Created attendance: {attendance.clock_in}")
    
    # Test timezone conversion
    local_tz = pytz.timezone(employee.location.timezone)
    local_time = attendance.clock_in.astimezone(local_tz)
    print(f"🕐 Clock-in in {employee.location.timezone}: {local_time.strftime('%I:%M %p')}")
    
    # Show current time in same timezone
    current_local = timezone.now().astimezone(local_tz)
    print(f"🕐 Current time in {employee.location.timezone}: {current_local.strftime('%I:%M %p')}")
    
    print("\n✅ Test attendance record created. Now test the home page!")

if __name__ == '__main__':
    create_test_attendance()