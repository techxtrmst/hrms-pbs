"""
Management command to create company admins for each tenant
Creates admin users for Petabytz, Bluebix, and Softstandard
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from companies.models import Company

User = get_user_model()


class Command(BaseCommand):
    help = "Create company admin users for each tenant"

    def handle(self, *args, **options):
        admins_data = [
            {
                "email": "admin@petabytz.com",
                "username": "petabytz_admin",
                "first_name": "Petabytz",
                "last_name": "Admin",
                "company_slug": "petabytz",
                "password": "admin123",  # Change this in production
            },
            {
                "email": "admin@bluebix.com",
                "username": "bluebix_admin",
                "first_name": "Bluebix",
                "last_name": "Admin",
                "company_slug": "bluebix",
                "password": "admin123",  # Change this in production
            },
            {
                "email": "admin@softstandard.com",
                "username": "softstandard_admin",
                "first_name": "Softstandard",
                "last_name": "Admin",
                "company_slug": "softstandard",
                "password": "admin123",  # Change this in production
            },
        ]

        for admin_data in admins_data:
            try:
                company = Company.objects.get(slug=admin_data["company_slug"])
            except Company.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Company {admin_data['company_slug']} not found. Run setup_companies first."
                    )
                )
                continue

            user, created = User.objects.update_or_create(
                email=admin_data["email"],
                defaults={
                    "username": admin_data["username"],
                    "first_name": admin_data["first_name"],
                    "last_name": admin_data["last_name"],
                    "company": company,
                    "role": User.Role.COMPANY_ADMIN,
                    "is_staff": True,
                    "is_active": True,
                    "must_change_password": False,  # Admin doesn't need to change password
                },
            )

            if created:
                user.set_password(admin_data["password"])
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created admin: {user.email} for {company.name}"
                    )
                )
            else:
                # Update password if user already exists
                user.set_password(admin_data["password"])
                user.save()
                self.stdout.write(
                    self.style.WARNING(
                        f"✓ Updated admin: {user.email} for {company.name}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "\n✓ Company admins created!\n"
                "Login credentials:\n"
                "  1. admin@petabytz.com / admin123\n"
                "  2. admin@bluebix.com / admin123\n"
                "  3. admin@softstandard.com / admin123\n"
                "\nNote: Change these passwords in production!\n"
            )
        )
