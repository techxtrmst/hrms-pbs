#!/usr/bin/env python
"""
Debug script to check leave balance issues after bulk upload
Run this script to diagnose leave balance problems
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveBalance
from accounts.models import User

def debug_leave_balances():
    print("=== LEAVE BALANCE DEBUG SCRIPT ===\n")
    
    # Get all employees with leave balances
    employees = Employee.objects.select_related('user', 'leave_balance').all()[:5]  # First 5 for testing
    
    for employee in employees:
        print(f"👤 Employee: {employee.user.get_full_name()} (ID: {employee.badge_id})")
        print(f"   Company: {employee.company.name}")
        
        try:
            # Try to access leave balance
            balance = employee.leave_balance
            print(f"   ✅ Leave Balance Found:")
            print(f"      CL Allocated: {balance.casual_leave_allocated}")
            print(f"      CL Used: {balance.casual_leave_used}")
            print(f"      CL Balance: {balance.casual_leave_balance}")
            print(f"      SL Allocated: {balance.sick_leave_allocated}")
            print(f"      SL Used: {balance.sick_leave_used}")
            print(f"      SL Balance: {balance.sick_leave_balance}")
            print(f"      Carry Forward: {balance.carry_forward_leave}")
            print(f"      Last Updated: {balance.updated_at}")
            
            # Test the property calculations
            expected_cl_balance = balance.casual_leave_allocated - balance.casual_leave_used
            expected_sl_balance = balance.sick_leave_allocated - balance.sick_leave_used
            
            if balance.casual_leave_balance == expected_cl_balance:
                print(f"      ✅ CL Balance calculation correct")
            else:
                print(f"      ❌ CL Balance calculation wrong: {balance.casual_leave_balance} != {expected_cl_balance}")
            
            if balance.sick_leave_balance == expected_sl_balance:
                print(f"      ✅ SL Balance calculation correct")
            else:
                print(f"      ❌ SL Balance calculation wrong: {balance.sick_leave_balance} != {expected_sl_balance}")
                
        except Exception as e:
            print(f"   ❌ Error accessing leave balance: {str(e)}")
            
            # Try to create leave balance
            try:
                balance = LeaveBalance.objects.create(
                    employee=employee,
                    casual_leave_allocated=0.0,
                    sick_leave_allocated=0.0
                )
                print(f"   ✅ Created new leave balance record")
            except Exception as create_error:
                print(f"   ❌ Error creating leave balance: {str(create_error)}")
        
        print()
    
    # Check for orphaned leave balances
    print("=== CHECKING FOR ORPHANED LEAVE BALANCES ===")
    all_balances = LeaveBalance.objects.select_related('employee__user').all()
    orphaned_count = 0
    
    for balance in all_balances:
        try:
            employee_name = balance.employee.user.get_full_name()
        except Exception:
            print(f"❌ Orphaned leave balance found: ID {balance.id}")
            orphaned_count += 1
    
    if orphaned_count == 0:
        print("✅ No orphaned leave balances found")
    else:
        print(f"❌ Found {orphaned_count} orphaned leave balance records")
    
    print("\n=== SUMMARY ===")
    total_employees = Employee.objects.count()
    total_balances = LeaveBalance.objects.count()
    print(f"Total Employees: {total_employees}")
    print(f"Total Leave Balances: {total_balances}")
    
    if total_employees == total_balances:
        print("✅ All employees have leave balance records")
    else:
        print(f"❌ Mismatch: {total_employees - total_balances} employees missing leave balances")

if __name__ == "__main__":
    debug_leave_balances()