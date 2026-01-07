
import os
import django
from django.conf import settings
from django.core.mail import send_mail

# 1. Update .env
env_path = '.env'
target_email = "hrms@petabytz.com"

lines = []
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        lines = f.readlines()

new_lines = []
keys_updated = set()

for line in lines:
    key = line.split('=')[0].strip()
    if key in ['DEFAULT_FROM_EMAIL', 'SERVER_EMAIL']:
        new_lines.append(f"{key}={target_email}\n")
        keys_updated.add(key)
    else:
        new_lines.append(line)

# Append if missing
if lines and not lines[-1].endswith('\n'):
    new_lines.append('\n')

if 'DEFAULT_FROM_EMAIL' not in keys_updated:
    new_lines.append(f"DEFAULT_FROM_EMAIL={target_email}\n")
if 'SERVER_EMAIL' not in keys_updated:
    new_lines.append(f"SERVER_EMAIL={target_email}\n")

with open(env_path, 'w') as f:
    f.writelines(new_lines)

print("Fixed .env FROM address settings.")

# 2. Test Again
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

print(f"Attempting to send email again from {settings.DEFAULT_FROM_EMAIL}...")
try:
    send_mail(
        'HRMS Email Test (Fixed)',
        'This email confirms that the SendAsDenied error is resolved.',
        settings.DEFAULT_FROM_EMAIL, # Should now be hrms@petabytz.com
        ['sathinath.padhi@petabytz.com'],
        fail_silently=False,
    )
    print("SUCCESS: Email sent successfully!")
except Exception as e:
    print(f"FAILURE: {e}")
