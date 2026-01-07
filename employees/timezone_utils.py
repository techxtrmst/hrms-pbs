"""
Timezone utilities for employee attendance system
"""

import pytz
from django.utils import timezone


def get_timezone_from_coordinates(lat, lng):
    """
    Get timezone from coordinates using a simple mapping
    In production, you'd use a service like Google Timezone API or timezonefinder
    """
    if not lat or not lng:
        return "Asia/Kolkata"  # Default timezone

    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        return "Asia/Kolkata"

    timezone_mapping = {
        # South Asia
        (20.5937, 78.9629): "Asia/Kolkata",  # India
        (23.6850, 90.3563): "Asia/Dhaka",  # Bangladesh
        (30.3753, 69.3451): "Asia/Karachi",  # Pakistan
        (7.8731, 80.7718): "Asia/Colombo",  # Sri Lanka
        (28.3949, 84.1240): "Asia/Kathmandu",  # Nepal
        (27.5142, 90.4336): "Asia/Thimphu",  # Bhutan
        # Middle East
        (23.4241, 53.8478): "Asia/Dubai",  # UAE
        (29.3117, 47.4818): "Asia/Kuwait",  # Kuwait
        (25.3548, 51.1839): "Asia/Qatar",  # Qatar
        (26.0667, 50.5577): "Asia/Bahrain",  # Bahrain
        (23.8859, 45.0792): "Asia/Riyadh",  # Saudi Arabia
        # Southeast Asia
        (1.3521, 103.8198): "Asia/Singapore",  # Singapore
        (4.2105, 101.9758): "Asia/Kuala_Lumpur",  # Malaysia
        (15.8700, 100.9925): "Asia/Bangkok",  # Thailand
        (12.8797, 121.7740): "Asia/Manila",  # Philippines
        (-0.7893, 113.9213): "Asia/Jakarta",  # Indonesia
        (21.0285, 105.8542): "Asia/Ho_Chi_Minh",  # Vietnam
        (11.5449, 104.8922): "Asia/Phnom_Penh",  # Cambodia
        (17.9757, 102.6331): "Asia/Vientiane",  # Laos
        (16.8409, 96.1735): "Asia/Yangon",  # Myanmar
        # East Asia
        (35.6762, 139.6503): "Asia/Tokyo",  # Japan
        (39.9042, 116.4074): "Asia/Shanghai",  # China
        (37.5665, 126.9780): "Asia/Seoul",  # South Korea
        (25.0330, 121.5654): "Asia/Taipei",  # Taiwan
        (22.3193, 114.1694): "Asia/Hong_Kong",  # Hong Kong
        (22.1987, 113.5439): "Asia/Macau",  # Macau
        # Europe
        (51.5074, -0.1278): "Europe/London",  # UK
        (48.8566, 2.3522): "Europe/Paris",  # France
        (52.5200, 13.4050): "Europe/Berlin",  # Germany
        (41.9028, 12.4964): "Europe/Rome",  # Italy
        (40.4168, -3.7038): "Europe/Madrid",  # Spain
        (52.3676, 4.9041): "Europe/Amsterdam",  # Netherlands
        (55.7558, 37.6176): "Europe/Moscow",  # Russia
        # North America
        (40.7128, -74.0060): "America/New_York",  # USA East Coast
        (34.0522, -118.2437): "America/Los_Angeles",  # USA West Coast
        (41.8781, -87.6298): "America/Chicago",  # USA Central
        (39.7392, -104.9903): "America/Denver",  # USA Mountain
        (43.6532, -79.3832): "America/Toronto",  # Canada East
        (49.2827, -123.1207): "America/Vancouver",  # Canada West
        (19.4326, -99.1332): "America/Mexico_City",  # Mexico
        # Australia & Oceania
        (-33.8688, 151.2093): "Australia/Sydney",  # Australia East
        (-31.9505, 115.8605): "Australia/Perth",  # Australia West
        (-37.8136, 144.9631): "Australia/Melbourne",  # Australia Southeast
        (-41.2865, 174.7762): "Pacific/Auckland",  # New Zealand
        # Africa
        (30.0444, 31.2357): "Africa/Cairo",  # Egypt
        (-26.2041, 28.0473): "Africa/Johannesburg",  # South Africa
        (6.5244, 3.3792): "Africa/Lagos",  # Nigeria
        (-1.2921, 36.8219): "Africa/Nairobi",  # Kenya
        # South America
        (-23.5505, -46.6333): "America/Sao_Paulo",  # Brazil
        (-34.6118, -58.3960): "America/Argentina/Buenos_Aires",  # Argentina
        (-12.0464, -77.0428): "America/Lima",  # Peru
        (4.7110, -74.0721): "America/Bogota",  # Colombia
    }

    # Find closest timezone based on coordinates
    min_distance = float("inf")
    closest_timezone = "Asia/Kolkata"  # Default to India

    for (ref_lat, ref_lng), tz in timezone_mapping.items():
        distance = ((lat - ref_lat) ** 2 + (lng - ref_lng) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            closest_timezone = tz

    return closest_timezone


def validate_timezone(timezone_str):
    """
    Validate if a timezone string is valid
    """
    if not timezone_str:
        return "Asia/Kolkata"

    try:
        pytz.timezone(timezone_str)
        return timezone_str
    except pytz.exceptions.UnknownTimeZoneError:
        return "Asia/Kolkata"


def convert_to_user_timezone(utc_datetime, user_timezone_str):
    """
    Convert UTC datetime to user's timezone
    """
    if not utc_datetime:
        return None

    try:
        user_tz = pytz.timezone(user_timezone_str)
        return utc_datetime.astimezone(user_tz)
    except pytz.exceptions.UnknownTimeZoneError:
        # Fallback to India timezone
        india_tz = pytz.timezone("Asia/Kolkata")
        return utc_datetime.astimezone(india_tz)


def get_current_time_in_timezone(timezone_str):
    """
    Get current time in specified timezone
    """
    try:
        tz = pytz.timezone(timezone_str)
        return timezone.now().astimezone(tz)
    except pytz.exceptions.UnknownTimeZoneError:
        # Fallback to India timezone
        india_tz = pytz.timezone("Asia/Kolkata")
        return timezone.now().astimezone(india_tz)


def get_timezone_display_name(timezone_str):
    """
    Get a user-friendly display name for timezone
    """
    timezone_names = {
        "Asia/Kolkata": "India Standard Time (IST)",
        "Asia/Dhaka": "Bangladesh Standard Time (BST)",
        "Asia/Karachi": "Pakistan Standard Time (PKT)",
        "Asia/Colombo": "Sri Lanka Standard Time (SLST)",
        "Asia/Kathmandu": "Nepal Time (NPT)",
        "Asia/Dubai": "Gulf Standard Time (GST)",
        "Asia/Singapore": "Singapore Standard Time (SGT)",
        "Asia/Bangkok": "Indochina Time (ICT)",
        "Asia/Manila": "Philippines Standard Time (PST)",
        "Asia/Jakarta": "Western Indonesia Time (WIB)",
        "Asia/Tokyo": "Japan Standard Time (JST)",
        "Asia/Shanghai": "China Standard Time (CST)",
        "Asia/Seoul": "Korea Standard Time (KST)",
        "Europe/London": "Greenwich Mean Time (GMT)",
        "Europe/Paris": "Central European Time (CET)",
        "Europe/Berlin": "Central European Time (CET)",
        "America/New_York": "Eastern Standard Time (EST)",
        "America/Los_Angeles": "Pacific Standard Time (PST)",
        "America/Chicago": "Central Standard Time (CST)",
        "Australia/Sydney": "Australian Eastern Standard Time (AEST)",
    }

    return timezone_names.get(timezone_str, timezone_str)
