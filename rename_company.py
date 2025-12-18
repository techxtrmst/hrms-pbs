import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from companies.models import Company

try:
    company = Company.objects.get(name='Peta Ytz')
    company.name = 'Petabytz'
    company.slug = 'petabytz'
    company.save()
    print("Successfully renamed Company 'Peta Ytz' to 'Petabytz'.")
except Company.DoesNotExist:
    print("Company 'Peta Ytz' not found (might have been renamed already).")
except Exception as e:
    print(f"Error: {e}")
