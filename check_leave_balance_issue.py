#!/usr/bin/env python
"""
Diagnostic script to check if allocated fields are being modified incorrectly
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveBalance, LeaveRequest
from datetime import date

def main():
    print("=== Leave Balance Diagnostic ===\n")
    
    # Get all employees with leave balances
    employees = Employee.objects.filter(leave_balance__isnull=False)
    
    print("Current Leave Balance Status:")
    print("-" * 80)
    print(f"{'Employee':<25} {'CL Alloc':<8} {'CL Used':<8} {'CL Bal':<8} {'SL Alloc':<8} {'SL Used':<8} {'SL Bal':<8}")
    print("-" * 80)
    
    for emp in employees:
        balance = emp.leave_balance
        print(f"{emp.user.get_full_name()[:24]:<25} "
              f"{balance.casual_leave_allocated:<8.1f} "
              f"{balance.casual_leave_used:<8.1f} "
              f"{balance.casual_leave_balance:<8.1f} "
              f"{balance.sick_leave_allocated:<8.1f} "
              f"{balance.sick_leave_used:<8.1f} "
              f"{balance.sick_leave_balance:<8.1f}")
    
    print("\n" + "=" * 80)
    print("EXPECTED BEHAVIOR:")
    print("- Allocated should remain constant (what admin sets)")
    print("- Used should increase when leaves are approved")
    print("- Balance should be calculated as: Allocated - Used")
    print("\nIf you see Allocated changing after leave approval, that's the bug!")
    
    # Check for any employees with non-zero allocations
    non_zero_employees = employees.filter(
        leave_balance__casual_leave_allocated__gt=0
    ).union(
        employees.filter(leave_balance__sick_leave_allocated__gt=0)
    )
    
    if non_zero_employees.exists():
        print(f"\nFound {non_zero_employees.count()} employees with allocated leaves.")
        print("You can test the leave approval process with these employees.")
    else:
        print("\nAll employees have 0 allocated leaves.")
        print("Allocate some leaves to test the approval process.")

if __name__ == '__main__':
    main()