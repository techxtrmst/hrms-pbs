from django.core.management.base import BaseCommand
from django.db.models import Q
from accounts.models import User
from employees.models import Employee


class Command(BaseCommand):
    help = 'Test the employee search API functionality'

    def handle(self, *args, **options):
        try:
            # Get a company admin user
            admin = User.objects.filter(role='COMPANY_ADMIN').first()
            if not admin:
                self.stdout.write(self.style.ERROR('No COMPANY_ADMIN user found'))
                return

            self.stdout.write(f'Testing with admin user: {admin.email}')
            self.stdout.write(f'Admin company: {admin.company.name if admin.company else "No Company"}')

            if not admin.company:
                self.stdout.write(self.style.ERROR('Admin user has no company assigned'))
                return

            # Test the search logic directly
            query = 's'
            self.stdout.write(f'Searching for: "{query}"')

            # Get employees in the same company
            employees = (
                Employee.objects.filter(company=admin.company)
                .filter(
                    Q(user__first_name__icontains=query) | 
                    Q(user__last_name__icontains=query) | 
                    Q(badge_id__icontains=query)
                )
                .select_related("user", "location", "manager")[:10]
            )

            self.stdout.write(f'Total employees in company: {Employee.objects.filter(company=admin.company).count()}')
            self.stdout.write(f'Employees matching "{query}": {employees.count()}')

            if employees.count() == 0:
                self.stdout.write(self.style.WARNING('No employees found matching the query'))
                
                # Show all employees in the company for debugging
                all_employees = Employee.objects.filter(company=admin.company)[:5]
                self.stdout.write('\nFirst 5 employees in company:')
                for emp in all_employees:
                    self.stdout.write(f'  - {emp.user.get_full_name()} (ID: {emp.badge_id}, First: {emp.user.first_name}, Last: {emp.user.last_name})')
            else:
                self.stdout.write('\nMatching employees:')
                for emp in employees:
                    result = {
                        "name": emp.user.get_full_name() or "No Name",
                        "employee_id": emp.badge_id or f"EMP-{emp.id}",
                        "department": emp.department or "N/A",
                        "location": emp.location.name if emp.location else "N/A",
                        "designation": emp.designation or "N/A",
                        "first_name": emp.user.first_name,
                        "last_name": emp.user.last_name,
                    }
                    self.stdout.write(f'  - {result}')

            self.stdout.write(self.style.SUCCESS('Search test completed successfully'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during search test: {str(e)}'))
            import traceback
            traceback.print_exc()