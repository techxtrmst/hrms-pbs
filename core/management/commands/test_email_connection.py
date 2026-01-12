from django.core.management.base import BaseCommand
from django.core.mail import get_connection, EmailMessage
from django.conf import settings


class Command(BaseCommand):
    help = "Test email connection settings"

    def add_arguments(self, parser):
        parser.add_argument("to_email", type=str, help="Recipient email address")
        parser.add_argument(
            "--password", type=str, help="Override settings password for testing"
        )

    def handle(self, *args, **options):
        to_email = options["to_email"]
        password = options.get("password")

        self.stdout.write("🔬 Testing Email Connection Options...")
        self.stdout.write(f"Sender: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"Recipient: {to_email}")

        # Method 1: Standard SMTP (port 587)
        self.stdout.write("\n------------------------------------------------")
        self.stdout.write("1. Testing Standard SMTP (smtp.office365.com:587)")

        try:
            connection = get_connection(
                host="smtp.office365.com",
                port=587,
                username=settings.EMAIL_HOST_USER,
                password=password or settings.EMAIL_HOST_PASSWORD,
                use_tls=True,
            )

            email = EmailMessage(
                "Test Email (Standard SMTP)",
                "This is a test email using authenticated SMTP.",
                settings.EMAIL_HOST_USER,
                [to_email],
                connection=connection,
            )
            email.send(fail_silently=False)
            self.stdout.write(
                self.style.SUCCESS("✅ SUCCESS! Authenticated SMTP works.")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ FAILED: {str(e)}"))
            if "5.7.139" in str(e):
                self.stdout.write(
                    self.style.WARNING(
                        "   -> This usually means MFA is blocking you. You NEED an App Password."
                    )
                )
            if "5.7.57" in str(e):
                self.stdout.write(
                    self.style.WARNING(
                        "   -> This means 'Authenticated SMTP' is disabled in Admin Center."
                    )
                )

        if "SUCCESS" not in locals().get("status_msg", ""):
            self.stdout.write(
                self.style.SUCCESS(
                    "✅ Configuration Test Complete. If Step 1 passed, your email system is ready."
                )
            )
