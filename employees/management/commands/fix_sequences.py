from django.core.management.base import BaseCommand
from django.db import connection, models
from employees.models import Employee, LeaveBalance


class Command(BaseCommand):
    help = "Fix PostgreSQL sequences for employee-related tables"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🔧 Fixing database sequences..."))

        # Fix Employee sequence
        max_employee_id = (
            Employee.objects.aggregate(max_id=models.Max("id"))["max_id"] or 0
        )

        with connection.cursor() as cursor:
            cursor.execute("SELECT last_value FROM employees_employee_id_seq;")
            employee_seq_value = cursor.fetchone()[0]

            if employee_seq_value <= max_employee_id:
                new_seq_value = max_employee_id + 1
                cursor.execute(
                    f"SELECT setval('employees_employee_id_seq', {new_seq_value});"
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Employee sequence updated: {employee_seq_value} → {new_seq_value}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Employee sequence is correct: {employee_seq_value}"
                    )
                )

        # Fix LeaveBalance sequence
        max_lb_id = (
            LeaveBalance.objects.aggregate(max_id=models.Max("id"))["max_id"] or 0
        )

        with connection.cursor() as cursor:
            cursor.execute("SELECT last_value FROM employees_leavebalance_id_seq;")
            lb_seq_value = cursor.fetchone()[0]

            if lb_seq_value <= max_lb_id:
                new_seq_value = max_lb_id + 1
                cursor.execute(
                    f"SELECT setval('employees_leavebalance_id_seq', {new_seq_value});"
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ LeaveBalance sequence updated: {lb_seq_value} → {new_seq_value}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ LeaveBalance sequence is correct: {lb_seq_value}"
                    )
                )

        self.stdout.write(self.style.SUCCESS("🎉 All sequences have been fixed!"))
