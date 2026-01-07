from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import smtplib


class Command(BaseCommand):
    help = "Test email sending configuration"

    def handle(self, *args, **kwargs):
        self.stdout.write("Testing email configuration...")
        self.stdout.write(f"Host: {settings.EMAIL_HOST}")
        self.stdout.write(f"Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"User: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"From: {settings.DEFAULT_FROM_EMAIL}")

        try:
            from_email = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL
            send_mail(
                "Test Email from HRMS",
                "This is a test email to verify configuration.",
                from_email,
                [settings.EMAIL_HOST_USER],  # Send to self for testing
                fail_silently=False,
            )
            self.stdout.write(
                self.style.SUCCESS("Successfully sent test email! Check your inbox.")
            )
        except smtplib.SMTPAuthenticationError as e:
            self.stdout.write(self.style.ERROR(f"Authentication Error: {e}"))
            self.stdout.write(
                self.style.ERROR(
                    "Please check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in settings.py"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to send email: {type(e).__name__}: {e}")
            )
