import os
import sys

import django

# Set up Django environment
print("Setting up Django environment...")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hrms_core.settings")
try:
    django.setup()
    print("Django setup complete.")
except Exception as e:
    print(f"Django setup failed: {e}")
    sys.exit(1)  # Exit if Django setup fails

from django.conf import settings
from django.core.mail import send_mail


def test_email():
    print("Testing email with following settings:")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    # print(f"EMAIL_HOST_PASSWORD: {settings.EMAIL_HOST_PASSWORD}") # Don't print password

    try:
        print("\nStarting send_mail...")
        send_mail(
            "Test Email",
            "This is a test email.",
            settings.EMAIL_HOST_USER,  # From
            ["hrms@petabytz.com"],  # To
            fail_silently=False,
        )
        print("\nSuccess! Email sent.")
    except Exception as e:
        print(f"\nFailed to send email. Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_email()
