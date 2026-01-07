#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, Attendance
from django.utils import timezone
from accounts.models import User
import pytz

def test_timezone_consistency():
    print("🕐 TESTING TIMEZONE CONSISTENCY")
    print("=" * 60)
    
    # Get test employee
    try:
        user = User.objects.get(email='softtest@example.com')
        employee = user.employee_profile
        
        print(f"👤 Employee: {employee.user.email}")
        print(f"📍 Location: {employee.location.name}")
        print(f"🌍 Timezone: {employee.location.timezone}")
        
        # Get current time in employee's timezone
        local_tz = pytz.timezone(employee.location.timezone)
        current_utc = timezone.now()
        current_local = current_utc.astimezone(local_tz)
        
        print(f"\n⏰ CURRENT TIME:")
        print(f"   UTC: {current_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Local ({employee.location.timezone}): {current_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Display Format: {current_local.strftime('%I:%M %p')}")
        
        # Get today's attendance
        today = timezone.localdate()
        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        
        if attendance and attendance.clock_in:
            print(f"\n🕐 CLOCK-IN TIME:")
            print(f"   Stored UTC: {attendance.clock_in.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Convert to local timezone (this is what template does)
            clock_in_local = attendance.clock_in.astimezone(local_tz)
            print(f"   Local ({employee.location.timezone}): {clock_in_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"   Display Format: {clock_in_local.strftime('%I:%M %p')}")
            
            # Test JavaScript format (what gets passed to JS)
            js_utc_format = attendance.clock_in.strftime('%Y-%m-%d %H:%M:%S')
            print(f"   JavaScript UTC Format: {js_utc_format}")
            
            print(f"\n✅ CONSISTENCY CHECK:")
            print(f"   Both times use timezone: {employee.location.timezone}")
            print(f"   Current time format: {current_local.strftime('%I:%M %p')}")
            print(f"   Clock-in time format: {clock_in_local.strftime('%I:%M %p')}")
            
            # Check if they're in the same timezone
            if current_local.tzinfo == clock_in_local.tzinfo:
                print(f"   ✅ TIMEZONE MATCH: Both times use {employee.location.timezone}")
            else:
                print(f"   ❌ TIMEZONE MISMATCH: Different timezones detected")
                
        else:
            print(f"\n⚠️  No clock-in record found for today")
            
        print(f"\n" + "=" * 60)
        print("🎯 EXPECTED BEHAVIOR:")
        print("1. Current time displays in employee's local timezone")
        print("2. Clock-in time displays in employee's local timezone") 
        print("3. Both times should show same timezone (Asia/Kolkata)")
        print("4. JavaScript receives UTC time and converts properly")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_timezone_consistency()