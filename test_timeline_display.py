#!/usr/bin/env python
"""
Test script to verify timeline display logic
"""

import os
import sys
import django
from datetime import date
from dateutil.relativedelta import relativedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee

def test_timeline_display():
    """Test timeline display for different probation scenarios"""
    
    print("=== Timeline Display Test ===\n")
    
    # Get a real employee to test with
    employee = Employee.objects.filter(
        date_of_joining__isnull=False,
        employment_status='ACTIVE'
    ).first()
    
    if not employee:
        print("No employees found for testing")
        return
    
    print(f"Testing with Employee: {employee.user.get_full_name()}")
    print(f"Joining Date: {employee.date_of_joining}")
    print(f"Current Role: {employee.designation}")
    print(f"Department: {employee.department}")
    print()
    
    # Get probation info
    probation_status = employee.get_probation_status()
    probation_date = employee.get_probation_end_date()
    
    print("=== Timeline Display ===")
    print("1. TODAY")
    print(f"   Current Role: {employee.designation}")
    print()
    
    if probation_status in ['COMPLETED', 'COMPLETED_TODAY']:
        print(f"2. {probation_date.strftime('%d %b, %Y')}")
        if probation_status == 'COMPLETED_TODAY':
            print("   🎉 Probation Completed (TODAY!)")
        else:
            print("   Probation Completed")
        print("   Confirmed Employee")
        print()
    
    print(f"3. {employee.date_of_joining.strftime('%d %b, %Y')}")
    print("   Joined Organization")
    print(f"   {employee.designation} • {employee.department}")
    print()
    
    print("=== Status Summary ===")
    print(f"Probation Status: {probation_status}")
    print(f"Probation End Date: {probation_date}")
    print(f"Is Completed: {employee.is_probation_completed()}")
    
    # Test different scenarios
    print("\n=== Testing Different Scenarios ===")
    
    scenarios = [
        ("New Employee (1 month)", date.today() - relativedelta(months=1)),
        ("Mid Probation (2 months)", date.today() - relativedelta(months=2)),
        ("Completing Today", date.today() - relativedelta(months=3)),
        ("Completed (6 months)", date.today() - relativedelta(months=6)),
    ]
    
    for scenario_name, joining_date in scenarios:
        temp_emp = Employee(date_of_joining=joining_date)
        status = temp_emp.get_probation_status()
        end_date = temp_emp.get_probation_end_date()
        
        print(f"\n{scenario_name}:")
        print(f"  Joining: {joining_date}")
        print(f"  Probation End: {end_date}")
        print(f"  Status: {status}")
        
        print("  Timeline would show:")
        print("  1. TODAY - Current Role")
        
        if status in ['COMPLETED', 'COMPLETED_TODAY']:
            celebration = "🎉 " if status == 'COMPLETED_TODAY' else ""
            print(f"  2. {end_date.strftime('%d %b, %Y')} - {celebration}Probation Completed")
        
        print(f"  3. {joining_date.strftime('%d %b, %Y')} - Joined Organization")

if __name__ == "__main__":
    test_timeline_display()