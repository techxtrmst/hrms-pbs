from django.core.management.base import BaseCommand
from employees.models import Employee, LeaveBalance


class Command(BaseCommand):
    help = "Accrue monthly leaves (1 CL, 1 SL) for all employees"

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting leave accrual process...")

        employees = Employee.objects.all()
        count = 0

        for employee in employees:
            balance, created = LeaveBalance.objects.get_or_create(employee=employee)

            # Accrue 1 CL and 1 SL
            balance.casual_leave_allocated += 1.0
            balance.sick_leave_allocated += 1.0

            balance.save()
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully accrued leaves for {count} employees.")
        )
