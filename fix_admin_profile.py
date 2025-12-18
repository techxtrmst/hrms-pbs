import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from companies.models import Company
from accounts.models import User
from employees.models import Employee

def setup_admin_data():
    try:
        # Get the admin user
        admin_user = User.objects.get(username='admin')
        print(f"Found admin user: {admin_user.username}")

        # 1. Update Role
        admin_user.role = User.Role.COMPANY_ADMIN
        admin_user.save()
        print("Updated admin role to COMPANY_ADMIN")

        # 2. Assign Company
        company, created = Company.objects.get_or_create(
            name="Petabytz",
            defaults={'domain': 'petabytz.com'}
        )
        admin_user.company = company
        admin_user.save()
        if created:
            print("Created company 'Petabytz'")
        else:
            print("Linked to existing company 'Petabytz'")

        # 3. Create Employee Profile (required for views)
        employee, created = Employee.objects.get_or_create(
            user=admin_user,
            defaults={
                'company': company,
                'designation': 'HR Administrator',
                'department': 'Human Resources',
                'badge_id': 'EMP001',
                'work_type': 'FT',
                # Basic defaults
                'mobile_number': '9999999999',
                'gender': 'M',
                'marital_status': 'S',
            }
        )
        if created:
            print("Created Employee profile for admin")
        else:
            print("Employee profile already exists")

        print("\nSUCCESS: Admin account restored with full permissions and profile.")

    except User.DoesNotExist:
        print("Error: User 'admin' not found! Please ensure superuser is created.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    setup_admin_data()
