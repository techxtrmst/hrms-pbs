import os
import django
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

try:
    url = reverse('observability:request_list')
    print(f"SUCCESS: {url}")
except Exception as e:
    print(f"FAILURE: {e}")
