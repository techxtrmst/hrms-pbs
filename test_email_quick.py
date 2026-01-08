"""
Quick test for activation email - run with: python manage.py shell < test_email_quick.py
"""
from django.contrib.auth import get_user_model
from employees.utils import send_activation_email
from core.email_utils import get_hr_email_connection
from django.test import RequestFactory

User = get_user_model()

print("="*60)
print("ACTIVATION EMAIL TEST")
print("="*60)

# Test email connection
print("\n1. Testing Email Connection...")
try:
    connection = get_hr_email_connection()
    print(f"   ✓ Host: {connection.host}")
    print(f"   ✓ Port: {connection.port}")
    print(f"   ✓ Username: {connection.username}")
    connection.open()
    print("   ✓ Connection successful!")
    connection.close()
except Exception as e:
    print(f"   ✗ Connection failed: {str(e)}")

# Find test users
print("\n2. Finding Test Users...")
test_users = User.objects.filter(
    company__name__in=['Softstandard', 'Bluebix', 'Petabytz']
).select_related('company', 'employee_profile').order_by('-id')[:3]

if test_users:
    print(f"   Found {test_users.count()} users:")
    for user in test_users:
        company_name = user.company.name if user.company else "No Company"
        print(f"   - {user.get_full_name()} ({user.email}) - {company_name}")
    
    # Test sending email to first user
    print("\n3. Testing Activation Email Send...")
    test_user = test_users[0]
    print(f"   Sending to: {test_user.email}")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/')
    request.META['HTTP_HOST'] = '127.0.0.1:8000'
    
    try:
        result = send_activation_email(test_user, request)
        if result:
            print("   ✓ Email sent successfully!")
        else:
            print("   ✗ Email send failed (check logs)")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
else:
    print("   ✗ No test users found")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
