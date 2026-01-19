#!/usr/bin/env python
"""
Diagnostic script to verify Saeed Syed's leave balance calculation
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveBalance, LeaveRequest
from datetime import date

def main():
    print("=== Saeed Syed Leave Balance Verification ===\n")
    
    # Find Saeed Syed (mentioned as having badge ID PBHYD154 - khardar mastan)
    try:
        employee = Employee.objects.get(badge_id='PBHYD154')
        print(f"Employee: {employee.user.get_full_name()}")
        print(f"Badge ID: {employee.badge_id}")
        print(f"Date of Joining: {employee.date_of_joining}")
        
        # Check if in probation
        if employee.date_of_joining:
            from datetime import timedelta
            probation_end = employee.date_of_joining + timedelta(days=90)
            is_probation = date.today() <= probation_end
            print(f"Probation Status: {'In Probation' if is_probation else 'Completed'}")
            if is_probation:
                print(f"Probation ends on: {probation_end}")
        
        print("\n--- Leave Balance ---")
        try:
            balance = employee.leave_balance
            print(f"CL Allocated: {balance.casual_leave_allocated}")
            print(f"CL Used: {balance.casual_leave_used}")
            print(f"CL Balance: {balance.casual_leave_balance}")
            print(f"SL Allocated: {balance.sick_leave_allocated}")
            print(f"SL Used: {balance.sick_leave_used}")
            print(f"SL Balance: {balance.sick_leave_balance}")
            print(f"Unpaid Leave: {balance.unpaid_leave}")
        except Exception as e:
            print(f"Error getting leave balance: {e}")
        
        print("\n--- Approved Leave Requests (Current Year) ---")
        current_year = date.today().year
        approved_requests = LeaveRequest.objects.filter(
            employee=employee,
            status='APPROVED',
            start_date__year=current_year
        ).order_by('start_date')
        
        if approved_requests.exists():
            total_cl = 0
            total_sl = 0
            total_ul = 0
            
            for request in approved_requests:
                days = request.total_days
                print(f"- {request.get_leave_type_display()}: {request.start_date} to {request.end_date} ({days} days)")
                
                if request.leave_type == 'CL':
                    total_cl += days
                elif request.leave_type == 'SL':
                    total_sl += days
                elif request.leave_type == 'UL':
                    total_ul += days
            
            print(f"\nTotal from approved requests:")
            print(f"- CL Used: {total_cl}")
            print(f"- SL Used: {total_sl}")
            print(f"- UL Used: {total_ul}")
            
            # Verify calculations
            print(f"\n--- Verification ---")
            print(f"CL Balance should be: {balance.casual_leave_allocated} - {total_cl} = {balance.casual_leave_allocated - total_cl}")
            print(f"CL Balance actually is: {balance.casual_leave_balance}")
            print(f"SL Balance should be: {balance.sick_leave_allocated} - {total_sl} = {balance.sick_leave_allocated - total_sl}")
            print(f"SL Balance actually is: {balance.sick_leave_balance}")
            
            if (balance.casual_leave_allocated - total_cl == balance.casual_leave_balance and 
                balance.sick_leave_allocated - total_sl == balance.sick_leave_balance):
                print("✅ Leave balance calculations are CORRECT!")
            else:
                print("❌ Leave balance calculations have discrepancies!")
        else:
            print("No approved leave requests found for current year")
            
    except Employee.DoesNotExist:
        print("Employee with badge ID 'PBHYD154' not found")
        print("\nSearching for employees with 'saeed' in name...")
        employees = Employee.objects.filter(user__first_name__icontains='saeed')
        for emp in employees:
            print(f"- {emp.user.get_full_name()} ({emp.badge_id})")

if __name__ == '__main__':
    main()