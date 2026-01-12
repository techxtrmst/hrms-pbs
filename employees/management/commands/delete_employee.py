from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Delete an employee and all related data by email address."

    def add_arguments(self, parser):
        parser.add_argument(
            "email", type=str, help="The email address of the employee to delete"
        )

    def handle(self, *args, **options):
        email = options["email"]

        try:
            user = User.objects.get(email=email)
            self.stdout.write(f"Found user: {user.get_full_name()} ({user.email})")

            # Confirm deletion
            self.stdout.write(
                self.style.WARNING(
                    f"Are you sure you want to PERMANENTLY DELETE current user {user.email} and ALL related data (Employee profile, Attendance, Leaves, etc.)?"
                )
            )
            confirm = input("Type 'yes' to confirm: ")

            if confirm.lower() == "yes":
                user.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully deleted user {email} and all related data."
                    )
                )
            else:
                self.stdout.write(self.style.WARNING("Deletion cancelled."))

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with email '{email}' not found."))
