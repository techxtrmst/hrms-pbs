import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from django.contrib.auth import get_user_model
from companies.models import Company

User = get_user_model()

# Create Companies
companies = ['Petabytz', 'BlueBlix', 'SoftStandards']
for name in companies:
    Company.objects.get_or_create(name=name, defaults={'slug': name.lower().replace(' ', '-')})
    print(f"Verified Company: {name}")

# Create/Verify Admin
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print("Superuser 'admin' created.")
else:
    print("Superuser 'admin' already exists.")

print("Verification Data Setup Complete.")
