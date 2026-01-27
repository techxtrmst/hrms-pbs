"""
Management command to set up multi-tenant companies
Creates Petabytz, Bluebix, and Softstandar with their respective configurations
"""

from django.core.management.base import BaseCommand
from companies.models import Company


class Command(BaseCommand):
    help = "Set up multi-tenant companies (Petabytz, Bluebix, Softstandar)"

    def handle(self, *args, **options):
        companies_data = [
            {
                "name": "Petabytz",
                "slug": "petabytz",
                "primary_domain": "petabytz.com",
                "allowed_domains": "petabytz.com,www.petabytz.com",
                "email_domain": "petabytz.com",
                "location": "INDIA",
                "contact_email": "admin@petabytz.com",
                "city": "Bangalore",
                "state": "Karnataka",
                "country": "India",
            },
            {
                "name": "Bluebix",
                "slug": "bluebix",
                "primary_domain": "bluebix.com",
                "allowed_domains": "bluebix.com,www.bluebix.com,bluebixinc.com",
                "email_domain": "bluebixinc.com",
                "location": "US",
                "contact_email": "admin@bluebixinc.com",
                "city": "New York",
                "state": "New York",
                "country": "United States",
            },
            {
                "name": "Softstandard",
                "slug": "softstandard",
                "primary_domain": "softstandard.com",
                "allowed_domains": "softstandard.com,www.softstandard.com,rmindstech.com,oppora.ai",
                "email_domain": "softstandard.com,rmindstech.com,oppora.ai",
                "location": "BOTH",
                "contact_email": "admin@softstandard.com",
                "city": "Multiple Locations",
                "state": "India & Dhaka",
                "country": "India & Bangladesh",
            },
        ]

        for company_data in companies_data:
            company, created = Company.objects.update_or_create(
                slug=company_data["slug"], defaults=company_data
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created company: {company.name} ({company.primary_domain})"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"✓ Updated company: {company.name} ({company.primary_domain})"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "\n✓ Multi-tenant setup complete!\n"
                "Companies created:\n"
                "  1. Petabytz (India) - petabytz.com\n"
                "  2. Bluebix (United States) - bluebix.com\n"
                "  3. Softstandard (India & Dhaka) - softstandard.com\n"
            )
        )
