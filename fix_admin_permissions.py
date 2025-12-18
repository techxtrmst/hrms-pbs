import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from django.contrib.auth import get_user_model
from companies.models import Company

User = get_user_model()

# Fetch Admin and a Company
try:
    admin_user = User.objects.get(username='admin')
    company = Company.objects.get(name='Peta Ytz')

    # Update Admin Profile
    admin_user.company = company
    admin_user.role = User.Role.COMPANY_ADMIN
    admin_user.save()

    print(f"SUCCESS: User 'admin' is now COMPANY_ADMIN of '{company.name}'")
except User.DoesNotExist:
    print("ERROR: User 'admin' not found.")
except Company.DoesNotExist:
    print("ERROR: Company 'Peta Ytz' not found.")
except Exception as e:
    print(f"ERROR: {e}")
