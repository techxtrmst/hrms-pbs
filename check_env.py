import os

import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hrms_core.settings")
django.setup()

from django.conf import settings

print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
pwd = settings.EMAIL_HOST_PASSWORD
print(f"PASSWORD_LENGTH: {len(pwd)}")
print(f"PASSWORD_START: {pwd[:2]}")
print(f"PASSWORD_END: {pwd[-2:]}")
