"""
Django management command to create admin user
Usage: python manage.py create_admin_user --email admin@bluebix.com --password bluebix123 --company "Bluebix"
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from accounts.models import User
from companies.models import Company


class Command(BaseCommand):
    help = 'Create admin user for a company'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='User email address')
        parser.add_argument('--password', type=str, required=True, help='Password')
        parser.add_argument('--company', type=str, required=True, help='Company name')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        company_name = options['company']
        
        try:
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(
                    self.style.WARNING(f'⚠️ User {email} already exists')
                )
                return
            
            # Find company
            company = Company.objects.filter(name__icontains=company_name).first()
            if not company:
                self.stdout.write(
                    self.style.ERROR(f'❌ Company "{company_name}" not found')
                )
                return
            
            # Create user
            user = User.objects.create(
                email=email,
                first_name='Admin',
                last_name='User',
                role=User.Role.COMPANY_ADMIN,
                company=company,
                is_active=True,
                password=make_password(password)
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Admin user created successfully')
            )
            self.stdout.write(f'Email: {email}')
            self.stdout.write(f'Password: {password}')
            self.stdout.write(f'Company: {company.name}')
            self.stdout.write(f'Role: {user.role}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating user: {str(e)}')
            )