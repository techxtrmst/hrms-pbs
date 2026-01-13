#!/usr/bin/env python
"""
Test to verify that LOP (Loss of Pay) is being counted correctly
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveBalance, LeaveRequest
from accounts.models import User
from datetime import date, timedelta

def test_lop_counting():
    """Test that LOP is counted correctly in various scenarios"""
    print("🧪 Testing LOP counting...")
    
    # Get any existing employee with leave balance
    employees_with_balance = Employee.objects.filter(leave_balance__isnull=False)
    
    if not employees_with_balance.exists():
        print("❌ No employees with leave balance found.")
        return
    
    employee = employees_with_balance.first()
    balance = employee.leave_balance
    admin_user = User.objects.filter(role=User.Role.COMPANY_ADMIN).first()
    
    if not admin_user:
        print("❌ No admin user found for approval tests.")
        return
    
    print(f"✅ Testing with employee: {employee.user.get_full_name()}")
    
    # Store original values
    original_cl_allocated = balance.casual_leave_allocated
    original_cl_used = balance.casual_leave_used
    original_sl_allocated = balance.sick_leave_allocated
    original_sl_used = balance.sick_leave_used
    original_unpaid = balance.unpaid_leave
    
    print(f"📊 Original balances:")
    print(f"   CL: {balance.casual_leave_balance} available")
    print(f"   SL: {balance.sick_leave_balance} available")
    print(f"   Unpaid: {balance.unpaid_leave}")
    
    # Test Scenario 1: User has 3 CL, applies for 5 CL
    print(f"\n📝 Test Scenario 1: CL with partial LOP")
    balance.casual_leave_allocated = 10.0
    balance.casual_leave_used = 7.0  # So available = 3.0
    balance.unpaid_leave = 0.0
    balance.save()
    
    print(f"   Set CL balance to 3 days available")
    
    leave_request_1 = LeaveRequest.objects.create(
        employee=employee,
        leave_type='CL',
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=5),
        duration='FULL',
        reason='Test 5-day casual leave'
    )
    
    print(f"   Created leave request for {leave_request_1.total_days} days")
    print(f"   Will have LOP: {leave_request_1.will_have_lop}")
    
    # Approve and check
    success = leave_request_1.approve_leave(admin_user)
    balance.refresh_from_db()
    
    print(f"   After approval:")
    print(f"     - CL Used: {balance.casual_leave_used} (should be 10.0)")
    print(f"     - CL Available: {balance.casual_leave_balance} (should be 0)")
    print(f"     - Unpaid Leave: {balance.unpaid_leave} (should be 2.0)")
    
    assert balance.casual_leave_balance == 0, f"CL balance should be 0, got {balance.casual_leave_balance}"
    assert balance.unpaid_leave == 2.0, f"Unpaid leave should be 2.0, got {balance.unpaid_leave}"
    
    print(f"   ✅ Scenario 1 passed: 3 CL used, 2 days went to LOP")
    
    # Test Scenario 2: User has 0 SL, applies for 3 SL (all LOP)
    print(f"\n📝 Test Scenario 2: SL with full LOP")
    balance.sick_leave_allocated = 5.0
    balance.sick_leave_used = 5.0  # So available = 0.0
    balance.unpaid_leave = 2.0  # Keep previous LOP
    balance.save()
    
    print(f"   Set SL balance to 0 days available")
    
    leave_request_2 = LeaveRequest.objects.create(
        employee=employee,
        leave_type='SL',
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=12),
        duration='FULL',
        reason='Test 3-day sick leave with no balance'
    )
    
    print(f"   Created leave request for {leave_request_2.total_days} days")
    print(f"   Will have LOP: {leave_request_2.will_have_lop}")
    
    # Approve and check
    success = leave_request_2.approve_leave(admin_user)
    balance.refresh_from_db()
    
    print(f"   After approval:")
    print(f"     - SL Used: {balance.sick_leave_used} (should be 5.0)")
    print(f"     - SL Available: {balance.sick_leave_balance} (should be 0)")
    print(f"     - Unpaid Leave: {balance.unpaid_leave} (should be 5.0)")
    
    assert balance.sick_leave_balance == 0, f"SL balance should be 0, got {balance.sick_leave_balance}"
    assert balance.unpaid_leave == 5.0, f"Unpaid leave should be 5.0, got {balance.unpaid_leave}"
    
    print(f"   ✅ Scenario 2 passed: 0 SL used, 3 days went to LOP (total LOP: 5)")
    
    # Test Scenario 3: Direct UL application
    print(f"\n📝 Test Scenario 3: Direct Unpaid Leave application")
    
    leave_request_3 = LeaveRequest.objects.create(
        employee=employee,
        leave_type='UL',
        start_date=date.today() + timedelta(days=20),
        end_date=date.today() + timedelta(days=21),
        duration='FULL',
        reason='Test direct unpaid leave'
    )
    
    print(f"   Created UL request for {leave_request_3.total_days} days")
    print(f"   Will have LOP: {leave_request_3.will_have_lop}")
    
    # Approve and check
    success = leave_request_3.approve_leave(admin_user)
    balance.refresh_from_db()
    
    print(f"   After approval:")
    print(f"     - Unpaid Leave: {balance.unpaid_leave} (should be 7.0)")
    
    assert balance.unpaid_leave == 7.0, f"Unpaid leave should be 7.0, got {balance.unpaid_leave}"
    
    print(f"   ✅ Scenario 3 passed: 2 days added to LOP (total LOP: 7)")
    
    # Summary
    print(f"\n📈 Final Summary:")
    print(f"   Total LOP accumulated: {balance.unpaid_leave} days")
    print(f"   CL Balance: {balance.casual_leave_balance} days")
    print(f"   SL Balance: {balance.sick_leave_balance} days")
    
    # Cleanup
    leave_request_1.delete()
    leave_request_2.delete()
    leave_request_3.delete()
    
    # Restore original values
    balance.casual_leave_allocated = original_cl_allocated
    balance.casual_leave_used = original_cl_used
    balance.sick_leave_allocated = original_sl_allocated
    balance.sick_leave_used = original_sl_used
    balance.unpaid_leave = original_unpaid
    balance.save()
    
    print(f"   ✅ Restored original values and cleaned up")
    print(f"\n🎉 LOP counting test completed successfully!")

if __name__ == "__main__":
    test_lop_counting()