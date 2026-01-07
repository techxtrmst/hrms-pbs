"""
Management command to create a test user for development
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from companies.models import Company
from accounts.models import User


class Command(BaseCommand):
    help = "Creates a test company and user for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            default="test@test.com",
            help="Email address for the test user",
        )
        parser.add_argument(
            "--password", type=str, default="test", help="Password for the test user"
        )
        parser.add_argument(
            "--company", type=str, default="Test Company", help="Company name"
        )
        parser.add_argument(
            "--role",
            type=str,
            default="COMPANY_ADMIN",
            choices=["SUPERADMIN", "COMPANY_ADMIN", "MANAGER", "EMPLOYEE"],
            help="User role",
        )

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]
        company_name = options["company"]
        role = options["role"]

        # Create or get company
        company, created = Company.objects.get_or_create(
            primary_domain="localhost",
            defaults={
                "name": company_name,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created company: {company.name}"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Company already exists: {company.name}")
            )

        # Create or update user
        try:
            user = User.objects.get(email=email)
            self.stdout.write(
                self.style.WARNING(f"⚠ User {email} already exists - updating...")
            )
            user.set_password(password)
            user.company = company
            user.role = role
            user.must_change_password = False
            user.is_staff = True if role in ["SUPERADMIN", "COMPANY_ADMIN"] else False
            user.is_superuser = True if role == "SUPERADMIN" else False
            user.save()
            self.stdout.write(self.style.SUCCESS(f"✓ Updated user: {email}"))
        except User.DoesNotExist:
            username = email.split("@")[0]
            user = User.objects.create(
                username=username,
                email=email,
                first_name="Test",
                last_name="User",
                company=company,
                role=role,
                must_change_password=False,
                is_staff=True if role in ["SUPERADMIN", "COMPANY_ADMIN"] else False,
                is_superuser=True if role == "SUPERADMIN" else False,
                is_active=True,
            )
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"✓ Created user: {email}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== User Created/Updated ==="))
        self.stdout.write(f"Email: {email}")
        self.stdout.write(f"Password: {password}")
        self.stdout.write(f"Role: {user.get_role_display()}")
        self.stdout.write(f"Company: {company.name}")
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("You can now login at http://127.0.0.1:8000/")
        )
