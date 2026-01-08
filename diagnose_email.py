"""
Email Configuration Diagnostic Tool
Run with: python manage.py shell

This script checks if activation emails can be sent successfully.
"""

print("="*70)
print("ACTIVATION EMAIL DIAGNOSTIC TOOL")
print("="*70)

# Step 1: Check Environment Configuration
print("\n[1/5] Checking Environment Configuration...")
try:
    from django.conf import settings
    import environ
    import os
    
    env = environ.Env()
    env_file = settings.BASE_DIR / '.env'
    
    if env_file.exists():
        print(f"  ✓ .env file found at: {env_file}")
        environ.Env.read_env(env_file)
        
        # Check required variables
        email_host = env('EMAIL_HOST', default=None)
        email_port = env('EMAIL_PORT', default=None)
        email_user = env('EMAIL_HOST_USER', default=None)
        hr_password = env('PETABYTZ_HR_EMAIL_PASSWORD', default=None)
        
        print(f"  ✓ EMAIL_HOST: {email_host}")
        print(f"  ✓ EMAIL_PORT: {email_port}")
        print(f"  ✓ EMAIL_HOST_USER: {email_user}")
        print(f"  ✓ PETABYTZ_HR_EMAIL_PASSWORD: {'***SET***' if hr_password else '***NOT SET***'}")
        
        if not hr_password:
            print("  ✗ WARNING: PETABYTZ_HR_EMAIL_PASSWORD is not set!")
    else:
        print(f"  ✗ .env file not found at: {env_file}")
except Exception as e:
    print(f"  ✗ Error: {str(e)}")

# Step 2: Test Email Connection
print("\n[2/5] Testing Email Connection...")
try:
    from core.email_utils import get_hr_email_connection
    
    connection = get_hr_email_connection()
    print(f"  ✓ Connection object created")
    print(f"    - Host: {connection.host}")
    print(f"    - Port: {connection.port}")
    print(f"    - Username: {connection.username}")
    print(f"    - Use TLS: {connection.use_tls}")
    
    # Try to open connection
    connection.open()
    print(f"  ✓ Connection opened successfully!")
    connection.close()
    print(f"  ✓ Connection closed successfully!")
    
except Exception as e:
    print(f"  ✗ Connection failed: {str(e)}")
    print(f"  ✗ Error type: {type(e).__name__}")

# Step 3: Check Template Exists
print("\n[3/5] Checking Email Template...")
try:
    import os
    template_path = os.path.join(
        settings.BASE_DIR,
        'accounts',
        'templates',
        'accounts',
        'emails',
        'activation_email.html'
    )
    
    if os.path.exists(template_path):
        print(f"  ✓ Template found at: {template_path}")
        file_size = os.path.getsize(template_path)
        print(f"  ✓ Template size: {file_size} bytes")
    else:
        print(f"  ✗ Template not found at: {template_path}")
except Exception as e:
    print(f"  ✗ Error: {str(e)}")

# Step 4: Find Test Users
print("\n[4/5] Finding Test Users...")
try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Find users from different companies
    companies = ['Softstandard', 'Bluebix', 'Petabytz']
    
    for company_name in companies:
        users = User.objects.filter(
            company__name__icontains=company_name
        ).select_related('company')[:2]
        
        if users:
            print(f"\n  {company_name}:")
            for user in users:
                has_profile = hasattr(user, 'employee_profile') and user.employee_profile
                profile_status = "✓ Has Profile" if has_profile else "✗ No Profile"
                print(f"    - {user.get_full_name()} ({user.email}) - {profile_status}")
        else:
            print(f"\n  {company_name}: No users found")
            
except Exception as e:
    print(f"  ✗ Error: {str(e)}")

# Step 5: Test Email Send (Optional - Commented Out)
print("\n[5/5] Email Send Test...")
print("  ℹ️  To test email sending, uncomment the code below and run again.")
print("  ℹ️  Make sure to use a test email address you can access!")

# UNCOMMENT BELOW TO TEST ACTUAL EMAIL SENDING
"""
try:
    from django.contrib.auth import get_user_model
    from employees.utils import send_activation_email
    from django.test import RequestFactory
    
    User = get_user_model()
    
    # CHANGE THIS to a test user email
    TEST_EMAIL = "your-test-email@example.com"
    
    user = User.objects.filter(email=TEST_EMAIL).first()
    
    if user:
        print(f"  Testing with user: {user.get_full_name()} ({user.email})")
        
        # Create mock request
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_HOST'] = '127.0.0.1:8000'
        
        # Send email
        result = send_activation_email(user, request)
        
        if result:
            print(f"  ✓ Email sent successfully to {user.email}!")
            print(f"  ✓ Check the inbox for activation email")
        else:
            print(f"  ✗ Email send failed. Check logs above for details.")
    else:
        print(f"  ✗ Test user not found: {TEST_EMAIL}")
        
except Exception as e:
    print(f"  ✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
"""

# Summary
print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)
print("\nNext Steps:")
print("1. If connection test failed, check .env file and email password")
print("2. If template not found, verify file path")
print("3. If users have no profile, check employee creation process")
print("4. To test actual email sending, uncomment Step 5 code above")
print("5. Check Django logs for detailed error messages")
print("\nFor more help, see: ACTIVATION_EMAIL_TROUBLESHOOTING.md")
print("="*70)
