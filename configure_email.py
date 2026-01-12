import os
from pathlib import Path

# Path to .env file
base_dir = Path(r"c:\Users\sathi\Downloads\hrms-pbs-main")
env_path = base_dir / ".env"

# Existing config to preserve
lines = []
if env_path.exists():
    with open(env_path, "r") as f:
        lines = f.readlines()

new_config = {
    "EMAIL_HOST_USER": "hrms@petabytz.com",
    "EMAIL_HOST_PASSWORD": "Rminds@0007",
    "DEFAULT_FROM_EMAIL": "hrms@petabytz.com",
    "SERVER_EMAIL": "hrms@petabytz.com",
    "EMAIL_HOST": "smtp.office365.com",
    "EMAIL_PORT": "587",
    "EMAIL_USE_TLS": "True",
    "EMAIL_USE_SSL": "False",
}

updated_lines = []
processed_keys = set()

# Update existing keys
for line in lines:
    line = line.strip()
    if not line or line.startswith("#"):
        updated_lines.append(line + "\n")
        continue

    try:
        key, value = line.split("=", 1)
        key = key.strip()
        if key in new_config:
            updated_lines.append(f"{key}={new_config[key]}\n")
            processed_keys.add(key)
        else:
            updated_lines.append(line + "\n")
    except ValueError:
        updated_lines.append(line + "\n")

# Add missing keys
for key, val in new_config.items():
    if key not in processed_keys:
        updated_lines.append(f"{key}={val}\n")

with open(env_path, "w") as f:
    f.writelines(updated_lines)

print("Updated .env successfully.")

# Now test connection
import django
from django.conf import settings
from django.core.mail import send_mail
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hrms_core.settings")
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))
django.setup()

try:
    print(f"Testing with: {settings.EMAIL_HOST_USER}")
    send_mail(
        "HRMS Email Configuration Test",
        "Your email configuration is working successfully!",
        settings.DEFAULT_FROM_EMAIL,
        ["hrms@petabytz.com"],  # Send to self for test
        fail_silently=False,
    )
    print("Test email sent successfully!")
except Exception as e:
    print(f"Failed to send email: {e}")
