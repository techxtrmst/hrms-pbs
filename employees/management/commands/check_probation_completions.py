"""
Django management command to check for probation completions and send emails
This command should be run daily to check if any employees completed their probation period today.

Usage:
    python manage.py check_probation_completions
    python manage.py check_probation_completions --test  # Test mode (no emails sent)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Employee
from core.email_utils import send_probation_completion_email
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check for probation completions and send emails to employees who completed probation today"

    def add_arguments(self, parser):
        parser.add_argument(
            "--test",
            action="store_true",
            help="Test mode - show who would receive emails without actually sending them",
        )

    def handle(self, *args, **options):
        test_mode = options["test"]

        if test_mode:
            self.stdout.write(
                self.style.WARNING("Running in TEST mode - no emails will be sent")
            )

        # Get current date
        today = timezone.now().date()
        self.stdout.write(f"Checking probation completions for: {today}")

        # Track statistics
        probation_completions = 0
        emails_sent = 0

        # Get all active employees with joining dates
        employees = Employee.objects.select_related("user", "company").filter(
            user__is_active=True,
            employment_status="ACTIVE",
            date_of_joining__isnull=False
        )

        self.stdout.write(f"Checking {employees.count()} active employees...")

        for employee in employees:
            # Calculate probation end date (exactly 3 months from joining)
            probation_end_date = employee.date_of_joining + relativedelta(months=3)

            # Check if probation completes today
            if probation_end_date == today:
                probation_completions += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n🎓 Probation Completion: {employee.user.get_full_name()}"
                    )
                )
                self.stdout.write(f"   Company: {employee.company.name}")
                self.stdout.write(f"   Employee ID: {employee.badge_id or f'EMP-{employee.id}'}")
                self.stdout.write(f"   Email: {employee.user.email}")
                self.stdout.write(f"   Joining Date: {employee.date_of_joining}")
                self.stdout.write(f"   Probation End Date: {probation_end_date}")
                self.stdout.write("   Status: Probation completed today!")

                if not test_mode:
                    # Send probation completion email
                    if send_probation_completion_email(employee):
                        emails_sent += 1
                        self.stdout.write(
                            f"   ✅ Probation completion email sent to: {employee.user.email}"
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f"   ❌ Failed to send email to: {employee.user.email}"
                            )
                        )
                else:
                    self.stdout.write(
                        f"   📧 Would send probation completion email to: {employee.user.email}"
                    )

        # Print summary
        self.stdout.write(self.style.SUCCESS("\n\n=== Summary ==="))
        self.stdout.write(f"Probation completions found today: {probation_completions}")

        if not test_mode:
            self.stdout.write(f"Emails sent successfully: {emails_sent}")
            if probation_completions > emails_sent:
                failed_emails = probation_completions - emails_sent
                self.stdout.write(
                    self.style.ERROR(f"Failed to send emails: {failed_emails}")
                )
        else:
            self.stdout.write("No emails sent (test mode)")

        if probation_completions == 0:
            self.stdout.write("No employees completed probation today.")
        
        self.stdout.write(self.style.SUCCESS("Command completed successfully."))