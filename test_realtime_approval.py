#!/usr/bin/env python
"""
Test real-time leave approval to see if LOP is being added immediately
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

def test_realtime_approval():
    """Test real-time leave approval"""
    print("🧪 Testing real-time leave approval...")
    
    # Find SoftTest user
    try:
        user = User.objects.get(username='softtest@example.com')
        employee = user.employee_profile
    except (User.DoesNotExist, AttributeError):
        print("❌ SoftTest user not found")
        return
    
    balance = employee.leave_balance
    admin_user = User.objects.filter(role=User.Role.COMPANY_ADMIN).first()
    
    if not admin_user:
        print("❌ No admin user found")
        return
    
    print(f"✅ Testing with employee: {employee.user.get_full_name()}")
    
    # Store original values
    original_sl_allocated = balance.sick_leave_allocated
    original_sl_used = balance.sick_leave_used
    original_unpaid = balance.unpaid_leave
    
    print(f"📊 Original balance state:")
    print(f"   SL Allocated: {balance.sick_leave_allocated}")
    print(f"   SL Used: {balance.sick_leave_used}")
    print(f"   SL Balance: {balance.sick_leave_balance}")
    print(f"   Unpaid Leave: {balance.unpaid_leave}")
    
    # Set up test scenario: 0.5 SL available
    balance.sick_leave_allocated = 1.0
    balance.sick_leave_used = 0.5  # So available = 0.5
    balance.unpaid_leave = 0.5  # Keep existing LOP
    balance.save()
    
    print(f"\n🔧 Set up test scenario:")
    print(f"   SL Available: {balance.sick_leave_balance}")
    print(f"   Current LOP: {balance.unpaid_leave}")
    
    # Create a new leave request for 1.0 day
    test_leave = LeaveRequest.objects.create(
        employee=employee,
        leave_type='SL',
        start_date=date.today() + timedelta(days=5),
        end_date=date.today() + timedelta(days=5),
        duration='FULL',
        reason='Test real-time approval - 1 day sick leave'
    )
    
    print(f"\n📝 Created leave request:")
    print(f"   Type: {test_leave.get_leave_type_display()}")
    print(f"   Days: {test_leave.total_days}")
    print(f"   Status: {test_leave.status}")
    
    print(f"\n⏰ Before approval:")
    balance.refresh_from_db()
    print(f"   SL Used: {balance.sick_leave_used}")
    print(f"   SL Balance: {balance.sick_leave_balance}")
    print(f"   LOP: {balance.unpaid_leave}")
    
    # Approve the leave
    print(f"\n🔧 Approving leave...")
    success = test_leave.approve_leave(admin_user)
    
    print(f"   Approval success: {success}")
    
    # Check balance immediately after approval
    print(f"\n⚡ Immediately after approval:")
    balance.refresh_from_db()
    print(f"   SL Used: {balance.sick_leave_used}")
    print(f"   SL Balance: {balance.sick_leave_balance}")
    print(f"   LOP: {balance.unpaid_leave}")
    
    # Expected values
    expected_sl_used = 1.0  # Should use all available (0.5) + previous (0.5) = 1.0
    expected_lop = 1.0      # Previous 0.5 + new excess 0.5 = 1.0
    
    print(f"\n📊 Expected vs Actual:")
    print(f"   Expected SL Used: {expected_sl_used}, Actual: {balance.sick_leave_used}")
    print(f"   Expected LOP: {expected_lop}, Actual: {balance.unpaid_leave}")
    
    if balance.sick_leave_used == expected_sl_used and balance.unpaid_leave == expected_lop:
        print(f"   ✅ Real-time approval worked correctly!")
    else:
        print(f"   ❌ Real-time approval failed!")
        
        # Let's debug what happened
        print(f"\n🔍 Debugging the issue...")
        
        # Check if the approve_leave method was called correctly
        test_leave.refresh_from_db()
        print(f"   Leave status: {test_leave.status}")
        print(f"   Approved by: {test_leave.approved_by}")
        print(f"   Approved at: {test_leave.approved_at}")
        
        # Manually test the apply_leave_deduction method
        print(f"\n🧪 Testing apply_leave_deduction manually...")
        
        # Reset to before state
        balance.sick_leave_used = 0.5
        balance.unpaid_leave = 0.5
        balance.save()
        
        print(f"   Before manual deduction:")
        print(f"     SL Used: {balance.sick_leave_used}")
        print(f"     LOP: {balance.unpaid_leave}")
        
        # Apply deduction manually
        balance.apply_leave_deduction('SL', 1.0)
        
        print(f"   After manual deduction:")
        print(f"     SL Used: {balance.sick_leave_used}")
        print(f"     LOP: {balance.unpaid_leave}")
    
    # Cleanup
    test_leave.delete()
    
    # Restore original values
    balance.sick_leave_allocated = original_sl_allocated
    balance.sick_leave_used = original_sl_used
    balance.unpaid_leave = original_unpaid
    balance.save()
    
    print(f"\n✅ Cleaned up and restored original values")

if __name__ == "__main__":
    test_realtime_approval()