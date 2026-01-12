"""
Django management command to send birthday and work anniversary emails
This command checks each employee's location timezone and sends emails
when it's the appropriate time in their local timezone.

Run this command every hour via Task Scheduler to check all timezones.

Usage:
    python manage.py send_birthday_anniversary_emails
    python manage.py send_birthday_anniversary_emails --test  # Test mode (no emails sent)
    python manage.py send_birthday_anniversary_emails --hour 9  # Send at specific hour in local time
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Employee
from core.email_utils import (
    send_birthday_email,
    send_anniversary_email,
    send_birthday_announcement,
    send_anniversary_announcement,
    send_probation_completion_email,
)
from dateutil.relativedelta import relativedelta
import pytz
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send birthday and work anniversary emails to employees based on their location timezone"

    def add_arguments(self, parser):
        parser.add_argument(
            "--test",
            action="store_true",
            help="Test mode - show who would receive emails without actually sending them",
        )
        parser.add_argument(
            "--hour",
            type=int,
            default=9,
            help="Hour of the day (in employee local time) to send emails (default: 9 for 9:00 AM)",
        )

    def handle(self, *args, **options):
        test_mode = options["test"]
        target_hour = options["hour"]

        if test_mode:
            self.stdout.write(
                self.style.WARNING("Running in TEST mode - no emails will be sent")
            )

        # Get current UTC time
        now_utc = timezone.now()
        self.stdout.write(
            f"Current UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )
        self.stdout.write(f"Target hour in employee local time: {target_hour}:00")

        # Track statistics
        birthday_count = 0
        anniversary_count = 0
        probation_count = 0
        birthday_emails_sent = 0
        anniversary_emails_sent = 0
        birthday_announcements_sent = 0
        anniversary_announcements_sent = 0
        probation_emails_sent = 0

        # Get all active employees with their locations
        all_employees = Employee.objects.select_related(
            "user", "company", "location"
        ).filter(user__is_active=True)

        # Group employees by company for announcements
        companies = {}
        for emp in all_employees:
            if emp.company.id not in companies:
                companies[emp.company.id] = {"company": emp.company, "employees": []}
            companies[emp.company.id]["employees"].append(emp)

        # Process each employee based on their location timezone
        processed_locations = set()

        for emp in all_employees:
            # Get employee's timezone
            if emp.location and emp.location.timezone:
                tz_name = emp.location.timezone
            else:
                tz_name = "Asia/Kolkata"  # Default timezone

            try:
                local_tz = pytz.timezone(tz_name)
            except:
                self.stdout.write(
                    self.style.WARNING(
                        f"Invalid timezone {tz_name} for {emp.user.get_full_name()}, using Asia/Kolkata"
                    )
                )
                local_tz = pytz.timezone("Asia/Kolkata")

            # Convert current UTC time to employee's local time
            local_time = now_utc.astimezone(local_tz)
            local_date = local_time.date()
            local_hour = local_time.hour

            # Log timezone info for first employee in each location
            location_key = f"{emp.company.id}_{tz_name}"
            if location_key not in processed_locations:
                processed_locations.add(location_key)
                self.stdout.write(f"\n📍 {emp.company.name} - {tz_name}:")
                self.stdout.write(
                    f"   Local time: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )

            # Only process if current hour matches target hour (within the same hour window)
            if local_hour != target_hour:
                continue

            # Check for birthday
            if (
                emp.dob
                and emp.dob.month == local_date.month
                and emp.dob.day == local_date.day
            ):
                birthday_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"\n🎂 Birthday: {emp.user.get_full_name()}")
                )
                self.stdout.write(f"   Company: {emp.company.name}")
                self.stdout.write(
                    f"   Location: {emp.location.name if emp.location else 'Not set'}"
                )
                self.stdout.write(f"   Timezone: {tz_name}")
                self.stdout.write(f"   Local time: {local_time.strftime('%I:%M %p')}")

                if not test_mode:
                    # Send individual birthday email
                    if send_birthday_email(emp):
                        birthday_emails_sent += 1
                        self.stdout.write(
                            f"   ✅ Birthday email sent to: {emp.user.email}"
                        )

                    # Send company-wide announcement
                    company_employees = companies[emp.company.id]["employees"]
                    announcement_count = send_birthday_announcement(
                        emp, company_employees
                    )
                    if announcement_count > 0:
                        birthday_announcements_sent += announcement_count
                        self.stdout.write(
                            f"   ✅ Announcement sent to {announcement_count} employees"
                        )
                else:
                    self.stdout.write(
                        f"   Would send birthday email to: {emp.user.email}"
                    )
                    company_employees = companies[emp.company.id]["employees"]
                    recipient_count = len(
                        [
                            e
                            for e in company_employees
                            if e.user.email and e.id != emp.id
                        ]
                    )
                    self.stdout.write(
                        f"   Would send announcement to {recipient_count} employees"
                    )

            # Check for work anniversary
            if (
                emp.date_of_joining
                and emp.date_of_joining.month == local_date.month
                and emp.date_of_joining.day == local_date.day
            ):
                # Calculate years of service
                years = local_date.year - emp.date_of_joining.year

                # Skip if it's their first day (0 years)
                if years == 0:
                    continue

                anniversary_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n🏆 Work Anniversary: {emp.user.get_full_name()}"
                    )
                )
                self.stdout.write(f"   Company: {emp.company.name}")
                self.stdout.write(
                    f"   Location: {emp.location.name if emp.location else 'Not set'}"
                )
                self.stdout.write(f"   Timezone: {tz_name}")
                self.stdout.write(f"   Local time: {local_time.strftime('%I:%M %p')}")
                self.stdout.write(f"   Years of service: {years}")

                if not test_mode:
                    # Send individual anniversary email
                    if send_anniversary_email(emp, years):
                        anniversary_emails_sent += 1
                        self.stdout.write(
                            f"   ✅ Anniversary email sent to: {emp.user.email}"
                        )

                    # Send company-wide announcement
                    company_employees = companies[emp.company.id]["employees"]
                    announcement_count = send_anniversary_announcement(
                        emp, years, company_employees
                    )
                    if announcement_count > 0:
                        anniversary_announcements_sent += announcement_count
                        self.stdout.write(
                            f"   ✅ Announcement sent to {announcement_count} employees"
                        )
                else:
                    self.stdout.write(
                        f"   Would send anniversary email to: {emp.user.email}"
                    )
                    company_employees = companies[emp.company.id]["employees"]
                    recipient_count = len(
                        [
                            e
                            for e in company_employees
                            if e.user.email and e.id != emp.id
                        ]
                    )
                    self.stdout.write(
                        f"   Would send announcement to {recipient_count} employees"
                    )

            # Check for probation completion (3 months from joining date)
            if emp.date_of_joining:
                # Calculate exactly 3 months from joining
                probation_end_date = emp.date_of_joining + relativedelta(months=3)

                if local_date == probation_end_date:
                    probation_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"\n🎓 Probation Completion: {emp.user.get_full_name()}"
                        )
                    )
                    self.stdout.write(f"   Company: {emp.company.name}")
                    self.stdout.write(
                        f"   Location: {emp.location.name if emp.location else 'Not set'}"
                    )
                    self.stdout.write(f"   Timezone: {tz_name}")
                    self.stdout.write(
                        f"   Local time: {local_time.strftime('%I:%M %p')}"
                    )
                    self.stdout.write(f"   Joining date: {emp.date_of_joining}")
                    self.stdout.write("   Probation completed: 3 months")

                    if not test_mode:
                        # Send probation completion email
                        if send_probation_completion_email(emp):
                            probation_emails_sent += 1
                            self.stdout.write(
                                f"   ✅ Probation completion email sent to: {emp.user.email}"
                            )
                    else:
                        self.stdout.write(
                            f"   Would send probation completion email to: {emp.user.email}"
                        )

        # Print summary
        self.stdout.write(self.style.SUCCESS("\n\n=== Summary ==="))
        self.stdout.write(f"Birthdays found (at target hour): {birthday_count}")
        self.stdout.write(
            f"Work anniversaries found (at target hour): {anniversary_count}"
        )
        self.stdout.write(f"Probation completions found: {probation_count}")

        if not test_mode:
            self.stdout.write(f"\nBirthday emails sent: {birthday_emails_sent}")
            self.stdout.write(
                f"Birthday announcements sent to: {birthday_announcements_sent} employees"
            )
            self.stdout.write(f"Anniversary emails sent: {anniversary_emails_sent}")
            self.stdout.write(
                f"Anniversary announcements sent to: {anniversary_announcements_sent} employees"
            )
            self.stdout.write(
                f"Probation completion emails sent: {probation_emails_sent}"
            )

            total_emails = (
                birthday_emails_sent
                + anniversary_emails_sent
                + birthday_announcements_sent
                + anniversary_announcements_sent
                + probation_emails_sent
            )
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Total emails sent: {total_emails}")
            )
        else:
            self.stdout.write(self.style.WARNING("\nNo emails sent (test mode)"))

        self.stdout.write(self.style.SUCCESS("\n✅ Command completed successfully"))
