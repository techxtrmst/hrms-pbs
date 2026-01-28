"""
Django management command to check employee currency settings
Usage: python manage.py check_employee_currency --name "jon cena"
"""

from django.core.management.base import BaseCommand
from employees.models import Employee
from companies.models import Location


class Command(BaseCommand):
    help = 'Check employee currency settings'

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, help='Employee name to search for')

    def handle(self, *args, **options):
        name = options.get('name')
        
        self.stdout.write("=== ALL LOCATIONS ===")
        for loc in Location.objects.all():
            self.stdout.write(f'{loc.name} - {loc.country_code} - Currency: {loc.currency} - Company: {loc.company.name}')
        
        self.stdout.write("\n=== ALL EMPLOYEES WITH LOCATIONS ===")
        employees = Employee.objects.select_related('user', 'location', 'company').all()
        
        for emp in employees:
            if name and name.lower() not in emp.user.get_full_name().lower():
                continue
                
            location_info = "None"
            currency_info = "None"
            country_info = "None"
            
            if emp.location:
                location_info = emp.location.name
                currency_info = emp.location.currency
                country_info = emp.location.country_code
            
            self.stdout.write(f'{emp.user.get_full_name()} - Location: {location_info} - Currency: {currency_info} - Country: {country_info} - Company: {emp.company.name if emp.company else "None"}')