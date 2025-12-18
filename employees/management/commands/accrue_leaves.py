from django.core.management.base import BaseCommand
from employees.models import Employee, LeaveBalance

class Command(BaseCommand):
    help = 'Accrues 1 Sick Leave and 1 Casual Leave for all active employees'

    def handle(self, *args, **options):
        employees = Employee.objects.all()
        count = 0
        for employee in employees:
            balance, created = LeaveBalance.objects.get_or_create(employee=employee)
            balance.casual_leave += 1.0
            balance.sick_leave += 1.0
            balance.save()
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully accrued leaves for {count} employees.'))
