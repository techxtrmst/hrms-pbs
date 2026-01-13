#!/usr/bin/env python
"""
Test the simplified leave system where users can apply for more leaves than available,
and excess goes to LOP when approved.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveBalance, LeaveRequest
from datetime import date, timedelta

def test_simplified_leave_system():
    """Test the simplified leave system"""
    print("🧪 Testing simplified leave system...")
    
    # Get any existing employee with leave balance
    employees_with_balance = Employee.objects.filter(leave_balance__isnull=False)
    
    if not employees_with_balance.exists():
        print("❌ No employees with leave balance found.")
        return
    
    employee = employees_with_balance.first()
    balance = employee.leave_balance
    
    print(f"✅ Testing with employee: {employee.user.get_full_name()}")
    print(f"📊 Current balances:")
    print(f"   SL - Allocated: {balance.sick_leave_allocated}, Used: {balance.sick_leave_used}")
    print(f"   SL - Available: {balance.sick_leave_balance}")
    print(f"   Unpaid: {balance.unpaid_leave}")
    
    # Store original values
    original_sl_used = balance.sick_leave_used
    original_unpaid = balance.unpaid_leave
    
    # Test scenario: User has 2 sick leaves, applies for 4
    print(f"\n📝 Test Scenario:")
    print(f"   Setting SL balance to 2 days available")
    
    # Set up test scenario
    balance.sick_leave_allocated = 5.0
    balance.sick_leave_used = 3.0  # So available = 2.0
    balance.unpaid_leave = 0.0
    balance.save()
    
    print(f"   SL Available: {balance.sick_leave_balance} days")
    
    # Create leave request for 4 days
    leave_request = LeaveRequest.objects.create(
        employee=employee,
        leave_type='SL',
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=4),
        duration='FULL',
        reason='Test 4-day sick leave'
    )
    
    print(f"   Created leave request for {leave_request.total_days} days")
    
    # Test validation
    validation = leave_request.validate_leave_application()
    print(f"   Validation result:")
    print(f"     - Can apply: {validation['is_valid']}")
    print(f"     - Available: {validation['available_balance']} days")
    print(f"     - Will be LOP: {validation['will_be_lop']}")
    print(f"     - Shortfall: {validation['shortfall']} days")
    print(f"     - Message: {validation['message']}")
    
    # Test approval
    print(f"\n🔧 Testing leave approval...")
    from accounts.models import User
    admin_user = User.objects.filter(role=User.Role.COMPANY_ADMIN).first()
    
    if admin_user:
        success = leave_request.approve_leave(admin_user)
        print(f"   Approval success: {success}")
        
        if success:
            # Check balance after approval
            balance.refresh_from_db()
            print(f"   After approval:")
            print(f"     - SL Used: {balance.sick_leave_used}")
            print(f"     - SL Available: {balance.sick_leave_balance}")
            print(f"     - Unpaid Leave: {balance.unpaid_leave}")
            
            # Verify the logic
            expected_sl_used = balance.sick_leave_allocated  # Should use all available (2 days)
            expected_unpaid = 2.0  # Excess 2 days should go to LOP
            
            assert balance.sick_leave_used == expected_sl_used, f"Expected SL used: {expected_sl_used}, got: {balance.sick_leave_used}"
            assert balance.sick_leave_balance == 0, f"Expected SL balance: 0, got: {balance.sick_leave_balance}"
            assert balance.unpaid_leave == expected_unpaid, f"Expected unpaid: {expected_unpaid}, got: {balance.unpaid_leave}"
            
            print(f"   ✅ Correct deduction: Used 2 SL days, 2 days went to LOP")
        else:
            print(f"   ❌ Approval failed")
    else:
        print(f"   ⚠️ No admin user found for approval test")
    
    # Restore original values
    balance.sick_leave_used = original_sl_used
    balance.unpaid_leave = original_unpaid
    balance.save()
    leave_request.delete()
    
    print(f"   ✅ Restored original values and cleaned up")
    print(f"\n🎉 Simplified leave system test completed!")

if __name__ == "__main__":
    test_simplified_leave_system()