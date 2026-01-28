"""
Django management command to list all users
Usage: python manage.py list_users
"""

from django.core.management.base import BaseCommand
from accounts.models import User
from companies.models import Company


class Command(BaseCommand):
    help = 'List all users in the system'

    def handle(self, *args, **options):
        self.stdout.write("=== USERS ===")
        for user in User.objects.all():
            company_name = getattr(user, 'company', None)
            if company_name:
                company_name = company_name.name
            else:
                company_name = "None"
            
            self.stdout.write(f'{user.email} - {user.role} - Company: {company_name}')
        
        self.stdout.write("\n=== COMPANIES ===")
        for company in Company.objects.all():
            self.stdout.write(f'{company.name} - ID: {company.id}')