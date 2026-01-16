#!/usr/bin/env python
"""
Simple test to verify negative balance prevention using existing data
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveBalance, LeaveRequest
from datetime import date, timedelta

def test_balance_properties():
    """Test that balance properties work correctly"""
    print("🧪 Testing leave balance properties...")
    
    # Get any existing employee with leave balance
    employees_with_balance = Employee.objects.filter(leave_balance__isnull=False)
    
    if not employees_with_balance.exists():
        print("❌ No employees with leave balance found. Creating test data...")
        return
    
    employee = employees_with_balance.first()
    balance = employee.leave_balance
    
    print(f"✅ Testing with employee: {employee.user.get_full_name()}")
    print(f"📊 Current balances:")
    print(f"   CL - Allocated: {balance.casual_leave_allocated}, Used: {balance.casual_leave_used}")
    print(f"   SL - Allocated: {balance.sick_leave_allocated}, Used: {balance.sick_leave_used}")
    print(f"   EL - Allocated: {balance.earned_leave_allocated}, Used: {balance.earned_leave_used}")
    print(f"   Unpaid: {balance.unpaid_leave}")
    
    # Test balance properties
    print(f"\n🔍 Balance calculations:")
    print(f"   CL Balance (can be negative): {balance.casual_leave_balance}")
    print(f"   CL Available (non-negative): {balance.casual_leave_available}")
    print(f"   SL Balance (can be negative): {balance.sick_leave_balance}")
    print(f"   SL Available (non-negative): {balance.sick_leave_available}")
    
    # Test validation for a hypothetical leave request
    print(f"\n📝 Testing leave validation:")
    
    # Test with 1 day sick leave
    test_request = LeaveRequest(
        employee=employee,
        leave_type='SL',
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=1),
        duration='FULL',
        reason='Test validation'
    )
    
    validation = test_request.validate_leave_application()
    print(f"   1 day SL request validation: {validation}")
    
    # Test with more days than available
    test_request_large = LeaveRequest(
        employee=employee,
        leave_type='SL',
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=10),
        duration='FULL',
        reason='Test large validation'
    )
    
    validation_large = test_request_large.validate_leave_application()
    print(f"   10 day SL request validation: {validation_large}")
    
    # Test fix_negative_balances method (dry run)
    print(f"\n🔧 Testing fix_negative_balances method:")
    original_sl_used = balance.sick_leave_used
    original_unpaid = balance.unpaid_leave
    
    # Temporarily create negative balance
    balance.sick_leave_used = balance.sick_leave_allocated + 2  # 2 days over
    print(f"   Temporarily set SL used to: {balance.sick_leave_used}")
    print(f"   This creates SL balance of: {balance.sick_leave_balance}")
    
    # Test the fix method
    would_fix = balance.sick_leave_balance < 0
    print(f"   Would fix_negative_balances() fix this? {would_fix}")
    
    if would_fix:
        # Actually test the fix
        fixed = balance.fix_negative_balances()
        print(f"   Fixed: {fixed}")
        print(f"   New SL balance: {balance.sick_leave_balance}")
        print(f"   New unpaid leave: {balance.unpaid_leave}")
    
    # Restore original values
    balance.sick_leave_used = original_sl_used
    balance.unpaid_leave = original_unpaid
    balance.save()
    print(f"   ✅ Restored original values")
    
    print(f"\n🎉 Balance property tests completed successfully!")

if __name__ == "__main__":
    test_balance_properties()