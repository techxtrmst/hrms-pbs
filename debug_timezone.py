#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from accounts.models import User
from employees.models import Employee, Attendance
from django.utils import timezone

def debug_timezone():
    print("🔍 DEBUGGING TIMEZONE ISSUE")
    print("=" * 50)
    
    # Check a test employee
    try:
        user = User.objects.get(email='softtest@example.com')
        employee = user.employee_profile
        print(f"👤 Employee: {employee.user.email}")
        print(f"🏢 Company: {employee.company.name}")
        print(f"📍 Location: {employee.location.name if employee.location else 'No location'}")
        print(f"🌍 Location Timezone: {employee.location.timezone if employee.location else 'No timezone'}")
        
        # Check attendance
        today = timezone.localdate()
        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        if attendance and attendance.clock_in:
            print(f"\n⏰ Clock-in time (UTC): {attendance.clock_in}")
            print(f"⏰ Clock-in time (Local): {timezone.localtime(attendance.clock_in)}")
            
            # Test timezone conversion
            if employee.location and employee.location.timezone:
                import pytz
                local_tz = pytz.timezone(employee.location.timezone)
                local_time = attendance.clock_in.astimezone(local_tz)
                print(f"⏰ Clock-in time ({employee.location.timezone}): {local_time}")
                print(f"⏰ Formatted: {local_time.strftime('%I:%M %p')}")
        else:
            print("\n❌ No attendance record found for today")
            
        # Check current time in different timezones
        print(f"\n🕐 Current UTC time: {timezone.now()}")
        print(f"🕐 Current Local time: {timezone.localtime()}")
        
        if employee.location and employee.location.timezone:
            import pytz
            local_tz = pytz.timezone(employee.location.timezone)
            current_local = timezone.now().astimezone(local_tz)
            print(f"🕐 Current {employee.location.timezone} time: {current_local}")
            print(f"🕐 Formatted: {current_local.strftime('%I:%M %p')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_timezone()