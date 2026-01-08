
import os
import django
import sys
from django.conf import settings
from django.core.mail import get_connection, EmailMultiAlternatives

# Add project root to sys.path
sys.path.append(os.getcwd())

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

import environ
env = environ.Env()

def test_smtp_connection():
    print("="*60)
    print("TESTING SMTP CONNECTION FOR hrms@petabytz.com")
    print("="*60)

    email_user = 'hrms@petabytz.com'
    email_pass = env('PETABYTZ_HR_EMAIL_PASSWORD', default='') # defaults to blank if not found
    
    # Check os.environ as fallback if not in .env (though environ.Env should check it)
    if not email_pass and 'PETABYTZ_HR_EMAIL_PASSWORD' in os.environ:
         email_pass = os.environ['PETABYTZ_HR_EMAIL_PASSWORD']

    if not email_pass:
        print("❌ ERROR: PETABYTZ_HR_EMAIL_PASSWORD is missing in .env file and os.environ")
        return False

    print(f"User: {email_user}")
    print(f"Password Length: {len(email_pass)}")

    try:
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host='smtp.office365.com',
            port=587,
            use_tls=True,
            username=email_user,
            password=email_pass,
            fail_silently=False,
        )
        
        print("\nAttempting to open connection...")
        connection.open()
        print("✅ Connection Successful!")
        connection.close()
        print("✅ Connection Closed")
        return True

    except Exception as e:
        print(f"\n❌ CONNECTION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_send_email():
    print("\n" + "="*60)
    print("TESTING SEND MAIL")
    print("="*60)
    
    email_user = 'hrms@petabytz.com'
    email_pass = env('PETABYTZ_HR_EMAIL_PASSWORD', default='')

    try:
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host='smtp.office365.com',
            port=587,
            use_tls=True,
            username=email_user,
            password=email_pass,
            fail_silently=False,
        )

        subject = "DEBUG TEST: HRMS Notification System Check 2"
        body = "This is a test email to verify that hrms@petabytz.com can send emails."
        from_email = f"Petabytz HR <{email_user}>"
        recipient_list = ['hrms@petabytz.com'] # Send to self first

        print(f"Sending from: {from_email}")
        print(f"Sending to: {recipient_list}")

        msg = EmailMultiAlternatives(subject, body, from_email, recipient_list, connection=connection)
        msg.send()
        
        print("✅ Email Sent Successfully to self!")
        
    except Exception as e:
        print(f"\n❌ SEND FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if test_smtp_connection():
        test_send_email()
