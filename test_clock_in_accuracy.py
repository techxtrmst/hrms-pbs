#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, Attendance
from django.utils import timezone
from django.test import Client
from django.contrib.auth import get_user_model
import pytz
import json

User = get_user_model()

def test_clock_in_accuracy():
    print("🕐 TESTING CLOCK-IN TIME ACCURACY")
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
        
        print(f"\n⏰ BEFORE CLOCK-IN:")
        print(f"   UTC Time: {current_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Local Time: {current_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Display Format: {current_local.strftime('%I:%M %p')}")
        
        # Delete existing attendance for today to test fresh clock-in
        today = timezone.localdate()
        Attendance.objects.filter(employee=employee, date=today).delete()
        print(f"\n🗑️  Cleared existing attendance for today")
        
        # Simulate clock-in (this is what happens when employee clicks clock-in)
        clock_in_time = timezone.now()
        attendance = Attendance.objects.create(
            employee=employee,
            date=today,
            clock_in=clock_in_time,
            status='PRESENT',
            location_in='0.0,0.0'  # Mock location
        )
        
        print(f"\n✅ CLOCK-IN COMPLETED:")
        print(f"   Stored UTC: {attendance.clock_in.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Convert stored time to local timezone (this is what template does)
        stored_local = attendance.clock_in.astimezone(local_tz)
        print(f"   Converted Local: {stored_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Display Format: {stored_local.strftime('%I:%M %p')}")
        
        # Test template conversion (simulate what Django template does)
        from django.template import Template, Context
        from django.template.loader import get_template
        
        # Test timezone conversion like in template
        template_str = """
        {% load tz %}
        {% timezone employee.location.timezone %}
            {{ attendance.clock_in|time:"h:i A" }}
        {% endtimezone %}
        """
        
        template = Template(template_str)
        context = Context({
            'employee': employee,
            'attendance': attendance
        })
        
        template_result = template.render(context).strip()
        print(f"   Template Result: {template_result}")
        
        # Check accuracy
        time_diff = abs((current_utc - clock_in_time).total_seconds())
        print(f"\n🎯 ACCURACY CHECK:")
        print(f"   Time difference: {time_diff:.2f} seconds")
        
        if time_diff < 2:  # Within 2 seconds
            print(f"   ✅ ACCURATE: Clock-in time captured correctly")
        else:
            print(f"   ❌ INACCURATE: Time difference too large")
        
        # Test late arrival calculation
        attendance.calculate_late_arrival()
        print(f"\n📊 LATE ARRIVAL CHECK:")
        print(f"   Is Late: {attendance.is_late}")
        print(f"   Late by: {attendance.late_by_minutes} minutes")
        print(f"   Grace Used: {attendance.is_grace_used}")
        
        print(f"\n" + "=" * 60)
        print("🎯 EXPECTED BEHAVIOR:")
        print("1. Clock-in time stored in UTC (for database consistency)")
        print("2. Display time converted to employee's local timezone")
        print("3. Current time and clock-in time show same timezone")
        print("4. Time difference should be minimal (< 2 seconds)")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_clock_in_accuracy()