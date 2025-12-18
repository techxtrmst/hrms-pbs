import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from django.contrib.auth import get_user_model
from employees.models import Employee
from companies.models import Company

User = get_user_model()

# Configuration
FIRST_NAME = 'Rajashekhar'
LAST_NAME = 'Reddy'
EMAIL = 'rajashekhar.reddy@petabytz.com'
PASSWORD = 'password123'
COMPANY_NAME = 'Petabytz'
ROLE = User.Role.COMPANY_ADMIN # Making him an admin as per context implying he wants to test admin rights

try:
    company = Company.objects.get(name=COMPANY_NAME)
except Company.DoesNotExist:
    print(f"Error: Company {COMPANY_NAME} does not exist. Using first available.")
    company = Company.objects.first()

if not company:
    print("No companies found. Run setup_data.py first.")
    exit()

# Check if user exists
if User.objects.filter(email=EMAIL).exists():
    print(f"User {EMAIL} already exists.")
    user = User.objects.get(email=EMAIL)
    user.set_password(PASSWORD)
    user.save()
    print("Password updated.")
else:
    # Create User
    user = User.objects.create_user(
        username=EMAIL,
        email=EMAIL,
        password=PASSWORD,
        first_name=FIRST_NAME,
        last_name=LAST_NAME,
        role=ROLE,
        company=company
    )
    print(f"User {EMAIL} created.")

# Ensure Employee Profile exists
employee, created = Employee.objects.get_or_create(
    user=user,
    defaults={
        'company': company,
        'badge_id': 'EMP_RAJ',
        'designation': 'Manager',
        'department': 'IT',
        'date_of_joining': date.today(),
        'mobile_number': '9876543210',
        'gender': 'M',
        'work_type': 'FT',
        'shift': 'General'
    }
)
if created:
    print("Employee profile created.")
else:
    print("Employee profile already exists.")

