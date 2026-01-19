"""
Test script to verify leave balance logic
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveRequest, LeaveBalance

# Test the leave balance logic
print("=" * 60)
print("LEAVE BALANCE LOGIC TEST")
print("=" * 60)

# Get a test employee
employees = Employee.objects.filter(is_active=True)[:3]

for emp in employees:
    print(f"\n👤 Employee: {emp.user.get_full_name()}")
    print("-" * 40)
    
    try:
        balance = emp.leave_balance
        print(f"Casual Leave Balance: {balance.casual_leave_balance}")
        print(f"Sick Leave Balance: {balance.sick_leave_balance}")
        print(f"Unpaid Leave: {balance.unpaid_leave}")
        
        # Get recent leave requests
        recent_leaves = LeaveRequest.objects.filter(employee=emp).order_by('-created_at')[:3]
        
        if recent_leaves:
            print(f"\nRecent Leave Requests:")
            for leave in recent_leaves:
                validation = leave.validate_leave_application()
                print(f"  📋 {leave.get_leave_type_display()}: {leave.total_days} days")
                print(f"     Status: {leave.status}")
                print(f"     Available: {validation.get('available_balance', 'N/A')}")
                print(f"     Will be LOP: {validation.get('will_be_lop', 'N/A')}")
                print(f"     is_negative_balance: {leave.is_negative_balance}")
                print(f"     Shortfall: {validation.get('shortfall', 'N/A')}")
                print()
        else:
            print("No recent leave requests")
            
    except Exception as e:
        print(f"Error: {e}")

print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)