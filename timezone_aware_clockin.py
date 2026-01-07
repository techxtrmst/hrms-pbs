#!/usr/bin/env python
"""
Enhanced Timezone-Aware Clock-in System

This system will:
1. Detect user's browser timezone
2. Store clock-in time in user's local timezone
3. Display times in user's local timezone
4. Handle employees from different countries correctly
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from django.utils import timezone
import pytz
from datetime import datetime

def get_timezone_from_coordinates(lat, lng):
    """
    Get timezone from coordinates using a simple mapping
    In production, you'd use a service like Google Timezone API
    """
    timezone_mapping = {
        # India
        (20.5937, 78.9629): 'Asia/Kolkata',
        # Bangladesh
        (23.6850, 90.3563): 'Asia/Dhaka',
        # Pakistan
        (30.3753, 69.3451): 'Asia/Karachi',
        # Sri Lanka
        (7.8731, 80.7718): 'Asia/Colombo',
        # Nepal
        (28.3949, 84.1240): 'Asia/Kathmandu',
        # UAE
        (23.4241, 53.8478): 'Asia/Dubai',
        # Singapore
        (1.3521, 103.8198): 'Asia/Singapore',
        # Malaysia
        (4.2105, 101.9758): 'Asia/Kuala_Lumpur',
        # Thailand
        (15.8700, 100.9925): 'Asia/Bangkok',
        # Philippines
        (12.8797, 121.7740): 'Asia/Manila',
        # Indonesia
        (-0.7893, 113.9213): 'Asia/Jakarta',
        # USA East Coast
        (40.7128, -74.0060): 'America/New_York',
        # USA West Coast
        (34.0522, -118.2437): 'America/Los_Angeles',
        # UK
        (55.3781, -3.4360): 'Europe/London',
        # Germany
        (51.1657, 10.4515): 'Europe/Berlin',
        # Australia
        (-25.2744, 133.7751): 'Australia/Sydney',
    }
    
    # Find closest timezone based on coordinates
    min_distance = float('inf')
    closest_timezone = 'Asia/Kolkata'  # Default to India
    
    for (ref_lat, ref_lng), tz in timezone_mapping.items():
        distance = ((lat - ref_lat) ** 2 + (lng - ref_lng) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            closest_timezone = tz
    
    return closest_timezone

def create_enhanced_clock_in_view():
    """
    Create the enhanced clock-in view code
    """
    
    clock_in_view_code = '''
@csrf_exempt
@login_required
def clock_in(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            lat = data.get("latitude")
            lng = data.get("longitude")
            
            # NEW: Get user's timezone from browser or coordinates
            user_timezone_str = data.get("timezone")  # From browser
            
            # If no timezone from browser, detect from coordinates
            if not user_timezone_str and lat and lng:
                user_timezone_str = get_timezone_from_coordinates(float(lat), float(lng))
            
            # Default to company timezone if nothing else works
            if not user_timezone_str:
                user_timezone_str = 'Asia/Kolkata'  # Default
            
            # Validate timezone
            try:
                user_timezone = pytz.timezone(user_timezone_str)
            except pytz.exceptions.UnknownTimeZoneError:
                user_timezone = pytz.timezone('Asia/Kolkata')
                user_timezone_str = 'Asia/Kolkata'

            # Ensure employee profile exists
            if not hasattr(request.user, "employee_profile"):
                return JsonResponse(
                    {"status": "error", "message": "No employee profile found"},
                    status=400,
                )

            employee = request.user.employee_profile
            
            # Get current date in user's timezone
            user_now = timezone.now().astimezone(user_timezone)
            today = user_now.date()

            # Try to get existing attendance record for today
            try:
                attendance = Attendance.objects.get(employee=employee, date=today)

                # Check if already clocked in
                if attendance.clock_in:
                    # Convert stored time to user's timezone for display
                    local_clock_in = attendance.clock_in.astimezone(user_timezone)
                    
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "You are already clocked in.",
                            "already_clocked_in": True,
                            "clock_in_time": local_clock_in.strftime("%H:%M:%S"),
                            "clock_in_timezone": user_timezone_str,
                        }
                    )

            except Attendance.DoesNotExist:
                # Create new attendance record
                attendance = Attendance(employee=employee, date=today)

            # Determine Status based on Type
            clock_in_type = data.get("type")
            if clock_in_type == "remote":
                status = "WFH"
            elif clock_in_type == "on_duty":
                status = "ON_DUTY"
            else:
                status = "PRESENT"

            # NEW: Set clock-in time in user's timezone, then convert to UTC for storage
            local_clock_in_time = user_now
            utc_clock_in_time = local_clock_in_time.astimezone(pytz.UTC)
            
            attendance.clock_in = utc_clock_in_time
            attendance.location_in = f"{lat},{lng}"
            attendance.status = status
            attendance.clock_in_attempts = 1
            
            # NEW: Store user's timezone for later reference
            attendance.user_timezone = user_timezone_str
            
            # Set daily clock tracking fields
            attendance.daily_clock_count = 1
            attendance.is_currently_clocked_in = True
            attendance.max_daily_clocks = 3

            # Start location tracking
            attendance.location_tracking_active = True

            # Calculate location tracking end time based on shift duration
            shift = employee.assigned_shift
            if shift:
                shift_duration = shift.get_shift_duration_timedelta()
                attendance.location_tracking_end_time = (
                    attendance.clock_in + shift_duration
                )
            else:
                from datetime import timedelta
                attendance.location_tracking_end_time = attendance.clock_in + timedelta(hours=9)

            # NEW: Calculate late arrival using user's timezone
            attendance.calculate_late_arrival_with_timezone(user_timezone)

            attendance.save()

            # Prepare response with user's local time
            response_data = {
                "status": "success",
                "time": local_clock_in_time.strftime("%H:%M:%S"),
                "timezone": user_timezone_str,
                "local_date": local_clock_in_time.strftime("%Y-%m-%d"),
                "location_tracking_active": True,
            }

            if hasattr(attendance, 'is_late') and attendance.is_late:
                response_data["is_late"] = True
                response_data["late_by_minutes"] = attendance.late_by_minutes
                response_data["message"] = (
                    f"Clocked in at {local_clock_in_time.strftime('%H:%M:%S')} ({user_timezone_str}). "
                    f"You are {attendance.late_by_minutes} minutes late."
                )
            else:
                response_data["message"] = (
                    f"Clocked in successfully at {local_clock_in_time.strftime('%H:%M:%S')} ({user_timezone_str})."
                )

            return JsonResponse(response_data)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Clock-in error: {str(e)}", exc_info=True)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)


def get_timezone_from_coordinates(lat, lng):
    """
    Get timezone from coordinates using a simple mapping
    """
    timezone_mapping = {
        # India
        (20.5937, 78.9629): 'Asia/Kolkata',
        # Bangladesh
        (23.6850, 90.3563): 'Asia/Dhaka',
        # Pakistan
        (30.3753, 69.3451): 'Asia/Karachi',
        # Sri Lanka
        (7.8731, 80.7718): 'Asia/Colombo',
        # Nepal
        (28.3949, 84.1240): 'Asia/Kathmandu',
        # UAE
        (23.4241, 53.8478): 'Asia/Dubai',
        # Singapore
        (1.3521, 103.8198): 'Asia/Singapore',
        # Malaysia
        (4.2105, 101.9758): 'Asia/Kuala_Lumpur',
        # Thailand
        (15.8700, 100.9925): 'Asia/Bangkok',
        # Philippines
        (12.8797, 121.7740): 'Asia/Manila',
        # Indonesia
        (-0.7893, 113.9213): 'Asia/Jakarta',
        # USA East Coast
        (40.7128, -74.0060): 'America/New_York',
        # USA West Coast
        (34.0522, -118.2437): 'America/Los_Angeles',
        # UK
        (55.3781, -3.4360): 'Europe/London',
        # Germany
        (51.1657, 10.4515): 'Europe/Berlin',
        # Australia
        (-25.2744, 133.7751): 'Australia/Sydney',
    }
    
    min_distance = float('inf')
    closest_timezone = 'Asia/Kolkata'
    
    for (ref_lat, ref_lng), tz in timezone_mapping.items():
        distance = ((lat - ref_lat) ** 2 + (lng - ref_lng) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            closest_timezone = tz
    
    return closest_timezone
'''
    
    return clock_in_view_code

def create_frontend_timezone_detection():
    """
    Create JavaScript code for timezone detection
    """
    
    js_code = '''
// Enhanced timezone-aware clock-in JavaScript
function getTimezoneInfo() {
    // Get user's timezone from browser
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const now = new Date();
    const offset = now.getTimezoneOffset();
    
    return {
        timezone: timezone,
        offset: offset,
        localTime: now.toISOString(),
        localTimeString: now.toLocaleString()
    };
}

function clockInWithTimezone(latitude, longitude, type = 'office') {
    const timezoneInfo = getTimezoneInfo();
    
    const data = {
        latitude: latitude,
        longitude: longitude,
        type: type,
        timezone: timezoneInfo.timezone,
        local_time: timezoneInfo.localTime,
        timezone_offset: timezoneInfo.offset
    };
    
    console.log('Clock-in data with timezone:', data);
    
    fetch('/employees/clock-in/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Clock-in response:', data);
        
        if (data.status === 'success') {
            // Update UI with local time
            updateClockInUI(data);
            showSuccessMessage(data.message);
        } else {
            showErrorMessage(data.message);
        }
    })
    .catch(error => {
        console.error('Clock-in error:', error);
        showErrorMessage('Clock-in failed. Please try again.');
    });
}

function updateClockInUI(data) {
    // Update the UI to show local time and timezone
    const timeElement = document.getElementById('clock-in-time');
    const timezoneElement = document.getElementById('clock-in-timezone');
    
    if (timeElement) {
        timeElement.textContent = data.time;
    }
    
    if (timezoneElement) {
        timezoneElement.textContent = data.timezone;
    }
    
    // Update any other UI elements
    const statusElement = document.getElementById('attendance-status');
    if (statusElement) {
        statusElement.textContent = 'Clocked In';
        statusElement.className = 'status-clocked-in';
    }
}

// Auto-detect location and timezone for clock-in
function autoClockIn(type = 'office') {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                clockInWithTimezone(lat, lng, type);
            },
            function(error) {
                console.error('Geolocation error:', error);
                // Fallback: clock-in without location
                clockInWithTimezone(null, null, type);
            }
        );
    } else {
        console.error('Geolocation not supported');
        clockInWithTimezone(null, null, type);
    }
}

// Display current time in user's timezone
function displayCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    const timeDisplay = document.getElementById('current-time-display');
    if (timeDisplay) {
        timeDisplay.innerHTML = `
            <div class="current-time">${timeString}</div>
            <div class="current-timezone">${timezone}</div>
        `;
    }
}

// Update time display every second
setInterval(displayCurrentTime, 1000);

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    displayCurrentTime();
    
    // Add event listeners for clock-in buttons
    const clockInBtn = document.getElementById('clock-in-btn');
    if (clockInBtn) {
        clockInBtn.addEventListener('click', function() {
            autoClockIn('office');
        });
    }
    
    const wfhClockInBtn = document.getElementById('wfh-clock-in-btn');
    if (wfhClockInBtn) {
        wfhClockInBtn.addEventListener('click', function() {
            autoClockIn('remote');
        });
    }
});
'''
    
    return js_code

if __name__ == '__main__':
    print("🌍 TIMEZONE-AWARE CLOCK-IN SYSTEM")
    print("=" * 60)
    
    # Test timezone detection
    test_coordinates = [
        (28.6139, 77.2090, "New Delhi, India"),
        (23.8103, 90.4125, "Dhaka, Bangladesh"),
        (24.8607, 67.0011, "Karachi, Pakistan"),
        (6.9271, 79.8612, "Colombo, Sri Lanka"),
        (40.7128, -74.0060, "New York, USA"),
        (51.5074, -0.1278, "London, UK"),
    ]
    
    print("🗺️ Testing timezone detection:")
    for lat, lng, location in test_coordinates:
        detected_tz = get_timezone_from_coordinates(lat, lng)
        local_time = datetime.now(pytz.timezone(detected_tz))
        print(f"📍 {location}: {detected_tz} - {local_time.strftime('%H:%M:%S %Z')}")
    
    print("\n" + "=" * 60)
    print("✅ Enhanced timezone-aware clock-in system ready!")
    print("📝 Next steps:")
    print("1. Update the clock-in view with timezone handling")
    print("2. Add JavaScript for browser timezone detection")
    print("3. Update the Attendance model to store user timezone")
    print("4. Test with employees from different countries")
    print("=" * 60)