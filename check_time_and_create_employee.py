#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from django.utils import timezone
from accounts.models import User
from employees.models import Employee
from companies.models import Company, ShiftSchedule, Location
from django.contrib.auth.hashers import make_password
import pytz

def check_time_and_create_employee():
    print("🕐 CHECKING CURRENT TIME AND CREATING TEST EMPLOYEE")
    print("=" * 60)
    
    # Check current time in different timezones
    utc_now = timezone.now()
    print(f"🌍 Current UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Check India timezone (most common for this HRMS)
    india_tz = pytz.timezone('Asia/Kolkata')
    india_time = utc_now.astimezone(india_tz)
    print(f"🇮🇳 Current India time: {india_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Check local timezone from Django settings
    from django.conf import settings
    if hasattr(settings, 'TIME_ZONE'):
        local_tz = pytz.timezone(settings.TIME_ZONE)
        local_time = utc_now.astimezone(local_tz)
        print(f"⚙️ Django TIME_ZONE ({settings.TIME_ZONE}): {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    print("\n" + "=" * 60)
    print("👤 CREATING NEW TEST EMPLOYEE")
    print("=" * 60)
    
    # Get or create a company
    company = Company.objects.first()
    if not company:
        print("❌ No company found. Please create a company first.")
        return
    
    print(f"🏢 Using company: {company.name}")
    
    # Get or create a location
    location = company.locations.first()
    if not location:
        location = Location.objects.create(
            company=company,
            name="Test Office",
            address="Test Address",
            latitude=12.9716,
            longitude=77.5946
        )
        print(f"📍 Created location: {location.name}")
    else:
        print(f"📍 Using location: {location.name}")
    
    # Get or create a shift schedule
    shift = company.shifts.first()
    if not shift:
        shift = ShiftSchedule.objects.create(
            company=company,
            name="General Shift",
            start_time="09:00:00",
            end_time="18:00:00"
        )
        print(f"⏰ Created shift: {shift.name} ({shift.start_time} - {shift.end_time})")
    else:
        print(f"⏰ Using shift: {shift.name} ({shift.start_time} - {shift.end_time})")
    
    # Create test employee credentials
    email = "testemployee@example.com"
    password = "test123"
    
    # Check if user already exists
    if User.objects.filter(email=email).exists():
        print(f"⚠️ User with email {email} already exists. Using existing user.")
        user = User.objects.get(email=email)
        # Update password
        user.password = make_password(password)
        user.save()
        print(f"🔑 Updated password for existing user")
    else:
        # Create new user
        user = User.objects.create(
            email=email,
            username=email,
            first_name="Test",
            last_name="Employee",
            role=User.Role.EMPLOYEE,
            company=company,
            is_active=True,
            password=make_password(password)
        )
        print(f"✅ Created new user: {email}")
    
    # Check if employee profile exists
    try:
        employee = user.employee_profile
        print(f"⚠️ Employee profile already exists for {email}")
    except Employee.DoesNotExist:
        # Create employee profile
        employee = Employee.objects.create(
            user=user,
            company=company,
            designation="Test Employee",
            department="Testing",
            badge_id=f"TEST{user.id}",
            location=location,
            assigned_shift=shift,
            date_of_joining=timezone.now().date(),
            is_active=True,
            employment_status="ACTIVE"
        )
        print(f"✅ Created employee profile")
    
    print("\n" + "=" * 60)
    print("🎯 TEST EMPLOYEE CREDENTIALS")
    print("=" * 60)
    print(f"📧 Email: {email}")
    print(f"🔑 Password: {password}")
    print(f"👤 Name: {user.get_full_name()}")
    print(f"🏢 Company: {company.name}")
    print(f"📍 Location: {location.name}")
    print(f"⏰ Shift: {shift.name} ({shift.start_time} - {shift.end_time})")
    print(f"🆔 Badge ID: {employee.badge_id}")
    
    print("\n" + "=" * 60)
    print("⏰ SHIFT TIMING ANALYSIS")
    print("=" * 60)
    
    # Analyze shift timing vs current time
    current_time = india_time.time()
    shift_start = shift.start_time
    shift_end = shift.end_time
    
    print(f"🕘 Current time: {current_time.strftime('%H:%M:%S')}")
    print(f"🕘 Shift start: {shift_start}")
    print(f"🕘 Shift end: {shift_end}")
    
    # Check if current time is within shift hours
    if shift_start <= current_time <= shift_end:
        print("✅ Current time is WITHIN shift hours - Good for testing clock-in")
    elif current_time < shift_start:
        print("⚠️ Current time is BEFORE shift start - Employee can clock-in early")
    else:
        print("⚠️ Current time is AFTER shift end - Employee would be late")
    
    # Calculate time difference
    from datetime import datetime, time
    current_dt = datetime.combine(timezone.now().date(), current_time)
    shift_start_dt = datetime.combine(timezone.now().date(), shift_start)
    
    time_diff = current_dt - shift_start_dt
    minutes_diff = time_diff.total_seconds() / 60
    
    if minutes_diff > 0:
        print(f"📊 Employee would be {int(minutes_diff)} minutes LATE")
    else:
        print(f"📊 Employee would be {int(abs(minutes_diff))} minutes EARLY")
    
    print("\n" + "=" * 60)
    print("🚀 READY FOR TESTING!")
    print("=" * 60)
    print("1. Login with the credentials above")
    print("2. Navigate to the employee dashboard")
    print("3. Try the clock-in functionality")
    print("4. Check if timing calculations are correct")
    print("=" * 60)

if __name__ == '__main__':
    check_time_and_create_employee()