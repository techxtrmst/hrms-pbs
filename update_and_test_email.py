
import os
import sys

# 1. Update .env
env_path = '.env'
target_config = {
    'EMAIL_HOST_USER': 'hrms@petabytz.com',
    'EMAIL_HOST_PASSWORD': 'Rminds@0007',
    'EMAIL_PORT': '587',
    'EMAIL_USE_TLS': 'True',
    # 'EMAIL_HOST': 'smtp.office365.com' # Commented out to respect existing if present, or fallback to settings default
}

lines = []
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        lines = f.readlines()

new_lines = []
updated_keys = set()

for line in lines:
    key = line.split('=')[0].strip()
    if key in target_config:
        new_lines.append(f"{key}={target_config[key]}\n")
        updated_keys.add(key)
    else:
        new_lines.append(line)

# Append missing
if lines and not lines[-1].endswith('\n'):
    new_lines.append('\n')

for key, value in target_config.items():
    if key not in updated_keys:
        new_lines.append(f"{key}={value}\n")

with open(env_path, 'w') as f:
    f.writelines(new_lines)

print("Updated .env with provided credentials.")

# 2. Test Email
# We need to set up Django
import django
from django.conf import settings
from django.core.mail import send_mail

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

print(f"Current Settings:")
print(f"HOST: {settings.EMAIL_HOST}")
print(f"PORT: {settings.EMAIL_PORT}")
print(f"USER: {settings.EMAIL_HOST_USER}")
print(f"TLS: {settings.EMAIL_USE_TLS}")

recipient = 'sathinath.padhi@petabytz.com'
print(f"Attempting to send email to {recipient}...")

try:
    send_mail(
        'HRMS Email Test',
        'This is a test email to verify configuration.',
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        fail_silently=False,
    )
    print("SUCCESS: Email sent successfully!")
except Exception as e:
    print(f"FAILURE: Could not send email.")
    print(f"Error: {str(e)}")
