#!/usr/bin/env python
"""
Test script to verify leave validation is working correctly
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveBalance, LeaveRequest
from accounts.models import User
from datetime import date, timedelta

def test_leave_validation():
    print("🧪 Testing Leave Validation Logic...")
    
    # Get a test employee
    employee = Employee.objects.first()
    if not employee:
        print("❌ No employees found")
        return
    
    print(f"Testing with employee: {employee.user.get_full_name()}")
    
    # Check current balance
    balance = employee.leave_balance
    print(f"Current SL balance: {balance.sick_leave_balance}")
    print(f"Current CL balance: {balance.casual_leave_balance}")
    
    # Test case: Apply for 3 days SL when only 1 is available
    test_leave = LeaveRequest(
        employee=employee,
        leave_type='SL',  # Sick Leave
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=3),  # 3 days
        duration='FULL'
    )
    
    print(f"\n📝 Testing leave application:")
    print(f"   Leave type: {test_leave.get_leave_type_display()}")
    print(f"   Days requested: {test_leave.total_days}")
    print(f"   Available balance: {balance.sick_leave_balance}")
    
    # Validate the application
    validation = test_leave.validate_leave_application()
    
    print(f"\n✅ Validation Results:")
    print(f"   Is valid: {validation.get('is_valid', False)}")
    print(f"   Will be LOP: {validation.get('will_be_lop', False)}")
    print(f"   Available: {validation.get('available_balance', 0)}")
    print(f"   Shortfall: {validation.get('shortfall', 0)}")
    print(f"   Message: {validation.get('message', 'No message')}")
    
    # Test the can_apply_leave method directly
    leave_check = balance.can_apply_leave('SL', 3.0)
    print(f"\n🔍 Direct balance check:")
    print(f"   Can apply: {leave_check['can_apply']}")
    print(f"   Available: {leave_check['available']}")
    print(f"   Shortfall: {leave_check['shortfall']}")
    print(f"   Will be LOP: {leave_check['will_be_lop']}")

if __name__ == "__main__":
    test_leave_validation()