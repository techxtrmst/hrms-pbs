"""
Test script to verify activation email functionality
"""
import os
import django
import sys

# Setup Django
sys.path.append(r'c:\Users\sathi\Downloads\hrms-pbs-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms.settings')
django.setup()

from django.contrib.auth import get_user_model
from employees.utils import send_activation_email
from core.email_utils import get_hr_email_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

User = get_user_model()

def test_email_connection():
    """Test if email connection is working"""
    print("="*60)
    print("Testing Email Connection...")
    print("="*60)
    
    try:
        connection = get_hr_email_connection()
        print("✓ Email connection created successfully")
        print(f"  Host: {connection.host}")
        print(f"  Port: {connection.port}")
        print(f"  Username: {connection.username}")
        print(f"  Use TLS: {connection.use_tls}")
        
        # Test connection
        connection.open()
        print("✓ Connection opened successfully")
        connection.close()
        print("✓ Connection closed successfully")
        
        return True
    except Exception as e:
        print(f"✗ Email connection failed: {str(e)}")
        return False

def test_activation_email():
    """Test sending activation email to a test user"""
    print("\n" + "="*60)
    print("Testing Activation Email...")
    print("="*60)
    
    try:
        # Find a test user (preferably from Softstandard or Bluebix)
        test_users = User.objects.filter(
            company__name__in=['Softstandard', 'Bluebix', 'Petabytz']
        ).order_by('-id')[:5]
        
        if not test_users:
            print("✗ No test users found")
            return False
        
        print(f"\nFound {test_users.count()} potential test users:")
        for i, user in enumerate(test_users, 1):
            company_name = user.company.name if user.company else "No Company"
            print(f"  {i}. {user.get_full_name()} ({user.email}) - {company_name}")
        
        # Test with the first user
        test_user = test_users[0]
        print(f"\nTesting with: {test_user.get_full_name()} ({test_user.email})")
        
        # Send activation email
        result = send_activation_email(test_user)
        
        if result:
            print("✓ Activation email sent successfully!")
            return True
        else:
            print("✗ Failed to send activation email")
            return False
            
    except Exception as e:
        print(f"✗ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_env_configuration():
    """Check if .env file has correct email configuration"""
    print("\n" + "="*60)
    print("Checking Environment Configuration...")
    print("="*60)
    
    from django.conf import settings
    import environ
    
    env = environ.Env()
    
    try:
        # Try to read .env file
        env_file = settings.BASE_DIR / '.env'
        if env_file.exists():
            print(f"✓ .env file found at: {env_file}")
            
            # Check for required variables
            required_vars = [
                'EMAIL_HOST',
                'EMAIL_PORT',
                'EMAIL_HOST_USER',
                'EMAIL_HOST_PASSWORD',
                'PETABYTZ_HR_EMAIL_PASSWORD'
            ]
            
            environ.Env.read_env(env_file)
            
            for var in required_vars:
                value = env(var, default=None)
                if value:
                    if 'PASSWORD' in var:
                        print(f"  ✓ {var}: ****** (set)")
                    else:
                        print(f"  ✓ {var}: {value}")
                else:
                    print(f"  ✗ {var}: NOT SET")
        else:
            print(f"✗ .env file not found at: {env_file}")
            
    except Exception as e:
        print(f"✗ Error reading .env: {str(e)}")

if __name__ == "__main__":
    print("\n🔍 ACTIVATION EMAIL DIAGNOSTIC TEST\n")
    
    # Run tests
    check_env_configuration()
    connection_ok = test_email_connection()
    
    if connection_ok:
        test_activation_email()
    else:
        print("\n⚠️  Skipping activation email test due to connection failure")
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
