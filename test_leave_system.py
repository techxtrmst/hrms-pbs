#!/usr/bin/env python
"""
Quick test script to verify leave management system functionality
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveBalance, LeaveRequest
from accounts.models import User
from datetime import date, timedelta

def test_leave_system():
    print("🧪 Testing Leave Management System...")
    
    # Test 1: Check if leave balances are created automatically
    print("\n1. Testing automatic leave balance creation...")
    employees_without_balance = Employee.objects.filter(leave_balance__isnull=True)
    print(f"   Employees without leave balance: {employees_without_balance.count()}")
    
    # Create leave balances for employees who don't have them
    for employee in employees_without_balance:
        balance = LeaveBalance.objects.create(
            employee=employee,
            casual_leave_allocated=12.0,
            sick_leave_allocated=12.0,
            earned_leave_allocated=12.0,
            comp_off_allocated=0.0
        )
        print(f"   ✅ Created leave balance for {employee.user.get_full_name()}")
    
    # Test 2: Check leave balance calculations
    print("\n2. Testing leave balance calculations...")
    sample_employee = Employee.objects.first()
    if sample_employee and hasattr(sample_employee, 'leave_balance'):
        balance = sample_employee.leave_balance
        print(f"   Employee: {sample_employee.user.get_full_name()}")
        print(f"   CL Balance: {balance.casual_leave_balance}")
        print(f"   SL Balance: {balance.sick_leave_balance}")
        print(f"   EL Balance: {balance.earned_leave_balance}")
        print(f"   Total Balance: {balance.total_balance}")
        
        # Test validation
        validation = balance.can_apply_leave('CL', 5.0)
        print(f"   Can apply 5 days CL: {validation['can_apply']}")
        print(f"   Available: {validation['available']}, Shortfall: {validation['shortfall']}")
    
    # Test 3: Test leave request validation
    print("\n3. Testing leave request validation...")
    if sample_employee:
        # Create a test leave request
        test_leave = LeaveRequest(
            employee=sample_employee,
            leave_type='CL',
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=3),
            duration='FULL'
        )
        
        validation = test_leave.validate_leave_application()
        print(f"   Leave validation result: {validation}")
        print(f"   Is valid: {validation.get('is_valid', False)}")
        print(f"   Message: {validation.get('message', 'No message')}")
    
    print("\n✅ Leave management system tests completed!")
    print("\n📋 Summary:")
    print(f"   - Total employees: {Employee.objects.count()}")
    print(f"   - Employees with leave balance: {Employee.objects.filter(leave_balance__isnull=False).count()}")
    print(f"   - Total leave requests: {LeaveRequest.objects.count()}")
    print(f"   - Pending leave requests: {LeaveRequest.objects.filter(status='PENDING').count()}")

if __name__ == "__main__":
    test_leave_system()