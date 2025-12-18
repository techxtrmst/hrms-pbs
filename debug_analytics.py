import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

try:
    import openpyxl
    print("openpyxl imported successfully")
except ImportError as e:
    print(f"Error importing openpyxl: {e}")

from employees.models import Employee, Attendance
from django.utils import timezone
from core.views import attendance_analytics

try:
    print("Testing DB query...")
    count = Employee.objects.count()
    print(f"Employee count: {count}")
    
    today = timezone.localtime().date()
    print(f"Today: {today}")
    
    att_count = Attendance.objects.filter(date=today).count()
    print(f"Attendance today count: {att_count}")
    
    print("DB queries successful.")
except Exception as e:
    print(f"DB Error: {e}")
