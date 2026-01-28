"""
Django management command to reset user password
Usage: python manage.py reset_user_password --email admin@bluebix.com --password newpassword123
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from accounts.models import User


class Command(BaseCommand):
    help = 'Reset password for a specific user'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='User email address')
        parser.add_argument('--password', type=str, required=True, help='New password')

    def handle(self, *args, **options):
        email = options['email']
        new_password = options['password']
        
        try:
            user = User.objects.get(email=email)
            user.password = make_password(new_password)
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Password successfully reset for {email}')
            )
            self.stdout.write(f'New password: {new_password}')
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User with email {email} does not exist')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error resetting password: {str(e)}')
            )