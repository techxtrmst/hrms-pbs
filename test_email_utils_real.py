
import os
import django
import sys
from datetime import date

# Add project root to sys.path
sys.path.append(os.getcwd())

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveRequest
from core.email_utils import send_leave_request_notification, send_regularization_request_notification
from django.contrib.auth import get_user_model

User = get_user_model()

def test_utils():
    print("="*60)
    print("TESTING CORE.EMAIL_UTILS")
    print("="*60)

    # 1. Get a valid employee
    employee = Employee.objects.first()
    if not employee:
        print("❌ No employees found in DB to test with.")
        return

    print(f"Testing with Employee: {employee.user.get_full_name()} ({employee.user.email})")

    if not employee.user.email:
        print("⚠️ Employee has no email. Setting temp email for test.")
        employee.user.email = 'test_employee@example.com' # Won't save, just for object
    
    # Ensure manager exists for test or handle it
    if not employee.manager:
        print("ℹ️ No manager assigned. Email will go to HR only.")

    # 2. Create Dummy Leave Request (Unsaved)
    leave_request = LeaveRequest(
        employee=employee,
        leave_type='CL',
        start_date=date.today(),
        end_date=date.today(),
        reason='Test Leave Request via Debug Script',
        duration='FULL'
    )
    # Mock creating timestamp
    from django.utils import timezone
    leave_request.created_at = timezone.now()

    print("\nAttempting send_leave_request_notification...")
    try:
        result = send_leave_request_notification(leave_request)
        print(f"Result: {result}")
        if result['hr']:
            print("✅ HR Email Sent (via function return)")
        else:
            print("❌ HR Email Failed (via function return)")
    except Exception as e:
        print(f"❌ Exception in send_leave_request_notification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_utils()
