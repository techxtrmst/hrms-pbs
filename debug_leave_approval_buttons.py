#!/usr/bin/env python3
"""
Debug script to check leave approval button logic
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveRequest, LeaveBalance
from accounts.models import User

def debug_leave_approval_logic():
    """Debug the leave approval button logic"""
    print("=== DEBUGGING LEAVE APPROVAL BUTTON LOGIC ===\n")
    
    # Get some pending leave requests
    pending_leaves = LeaveRequest.objects.filter(status='PENDING').select_related(
        'employee', 'employee__user', 'employee__leave_balance'
    )[:5]
    
    if not pending_leaves.exists():
        print("No pending leave requests found.")
        return
    
    for leave in pending_leaves:
        print(f"Employee: {leave.employee.user.get_full_name()}")
        print(f"Leave Type: {leave.get_leave_type_display()}")
        print(f"Requested Days: {leave.total_days}")
        print(f"Start Date: {leave.start_date}")
        print(f"End Date: {leave.end_date}")
        
        # Get leave balance
        try:
            balance = leave.employee.leave_balance
            print(f"Current Balance:")
            print(f"  - CL Balance: {balance.casual_leave_balance}")
            print(f"  - SL Balance: {balance.sick_leave_balance}")
            print(f"  - LOP: {balance.unpaid_leave}")
            
            # Check validation
            validation = leave.validate_leave_application()
            print(f"Validation Result:")
            print(f"  - Available Balance: {validation.get('available_balance', 'N/A')}")
            print(f"  - Shortfall: {validation.get('shortfall', 'N/A')}")
            print(f"  - Will be LOP: {validation.get('will_be_lop', 'N/A')}")
            print(f"  - is_negative_balance: {leave.is_negative_balance}")
            
            # Determine which buttons should show
            if leave.is_negative_balance:
                print("BUTTONS TO SHOW: Reject, Approve Available, Approve with LOP")
            else:
                print("BUTTONS TO SHOW: Approve, Reject")
                
        except Exception as e:
            print(f"Error getting balance: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    debug_leave_approval_logic()