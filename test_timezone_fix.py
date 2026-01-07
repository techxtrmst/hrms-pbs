#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, Attendance
from django.utils import timezone
import pytz

def test_all_employees():
    print("🧪 TESTING TIMEZONE FIX FOR ALL EMPLOYEES")
    print("=" * 60)
    
    test_emails = [
        'bluebixtest@example.com',
        'softtest@example.com', 
        'william.jack@petabytzit.com',
        'employee@example.com',
        'uday.kiran@gmail.com'
    ]
    
    today = timezone.localdate()
    
    for email in test_emails:
        try:
            employee = Employee.objects.get(user__email=email)
            print(f"\n👤 {email}")
            print(f"   Location: {employee.location.name if employee.location else 'No location'}")
            print(f"   Timezone: {employee.location.timezone if employee.location else 'No timezone'}")
            
            # Check/create attendance
            attendance = Attendance.objects.filter(employee=employee, date=today).first()
            if not attendance:
                attendance = Attendance.objects.create(
                    employee=employee,
                    date=today,
                    clock_in=timezone.now(),
                    status='PRESENT'
                )
                print(f"   ✅ Created attendance record")
            else:
                print(f"   ✅ Attendance record exists")
            
            # Show timezone conversion
            if employee.location and employee.location.timezone:
                local_tz = pytz.timezone(employee.location.timezone)
                local_time = attendance.clock_in.astimezone(local_tz)
                current_local = timezone.now().astimezone(local_tz)
                
                print(f"   🕐 Clock-in: {local_time.strftime('%I:%M %p')}")
                print(f"   🕐 Current:  {current_local.strftime('%I:%M %p')}")
                print(f"   ✅ Both times in {employee.location.timezone}")
            else:
                print(f"   ❌ No timezone - times will be inconsistent")
                
        except Employee.DoesNotExist:
            print(f"❌ Employee not found: {email}")
    
    print(f"\n" + "=" * 60)
    print("🎯 EXPECTED RESULT:")
    print("- Current Time and Clock-in Time should show SAME timezone")
    print("- Both should display in Asia/Kolkata (Indian Standard Time)")
    print("- No more UTC vs Local time confusion")
    print("=" * 60)

if __name__ == '__main__':
    test_all_employees()