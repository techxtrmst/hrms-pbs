"""
Management command to update Bluebix company email domains
Adds bluebixinc.com to allowed domains
"""

from django.core.management.base import BaseCommand

from companies.models import Company


class Command(BaseCommand):
    help = "Update Bluebix company to allow bluebixinc.com email domain"

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(slug="bluebix")

            # Update allowed_domains
            current_domains = company.allowed_domains
            if "bluebixinc.com" not in current_domains:
                company.allowed_domains = f"{current_domains},bluebixinc.com"
                self.stdout.write(f"Updated allowed_domains: {company.allowed_domains}")

            # Update email_domain
            current_email_domains = company.email_domain
            if "bluebixinc.com" not in current_email_domains:
                company.email_domain = f"{current_email_domains},bluebixinc.com"
                self.stdout.write(f"Updated email_domain: {company.email_domain}")

            company.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n[SUCCESS] Bluebix company updated!\n"
                    f"Allowed domains: {company.allowed_domains}\n"
                    f"Email domains: {company.email_domain}\n"
                )
            )

        except Company.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("[ERROR] Bluebix company not found. Run 'python manage.py setup_companies' first.")
            )
