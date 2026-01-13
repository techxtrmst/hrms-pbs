#!/usr/bin/env python
"""
Test script to verify that negative leave balances are prevented
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from employees.models import Employee, LeaveBalance, LeaveRequest
from companies.models import Company, Location
from datetime import date, timedelta

User = get_user_model()

def test_negative_balance_prevention():
    """Test that negative balances are prevented and converted to LOP"""
    print("🧪 Testing negative balance prevention...")
    
    # Create test company and location
    company, created = Company.objects.get_or_create(
        name="Test Company Balance",
        defaults={
            "primary_domain": "testbalance.com",
            "email_domain": "testbalance.com"
        }
    )
    
    location, created = Location.objects.get_or_create(
        name="Test Location Balance",
        defaults={
            "company": company,
            "timezone": "Asia/Kolkata"
        }
    )
    
    # Create test user and employee
    import uuid
    unique_username = f"testuser_{uuid.uuid4().hex[:8]}"
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    user = User.objects.create_user(
        username=unique_username,
        email=unique_email,
        password="testpass123",
        first_name="Test",
        last_name="User",
        company=company
    )
    
    employee = Employee.objects.create(
        user=user,
        company=company,
        location=location,
        designation="Test Employee",
        department="Testing"
    )
    
    # Create leave balance with limited sick leave
    balance = LeaveBalance.objects.create(
        employee=employee,
        casual_leave_allocated=12.0,
        sick_leave_allocated=3.0,  # Only 3 days
        earned_leave_allocated=12.0,
        comp_off_allocated=0.0
    )
    
    print(f"✅ Created employee with SL balance: {balance.sick_leave_available} days")
    
    # Test 1: Try to apply for more sick leave than available
    print("\n📝 Test 1: Applying for 5 days SL when only 3 days available...")
    
    leave_request = LeaveRequest(
        employee=employee,
        leave_type='SL',
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=5),
        duration='FULL',
        reason='Test sick leave'
    )
    
    validation = leave_request.validate_leave_application()
    print(f"Validation result: {validation}")
    
    assert validation['will_be_lop'] == True, "Should require LOP confirmation"
    assert validation['available_balance'] == 3.0, "Should show 3 days available"
    assert validation['shortfall'] == 2.0, "Should show 2 days shortfall"
    
    print("✅ Validation correctly identified insufficient balance")
    
    # Test 2: Simulate approval and check balance deduction
    print("\n📝 Test 2: Simulating leave approval...")
    
    leave_request.save()  # Save the leave request
    
    # Simulate approval
    if leave_request.approve_leave(user):
        balance.refresh_from_db()
        print(f"After approval - SL used: {balance.sick_leave_used}")
        print(f"After approval - SL balance: {balance.sick_leave_balance}")
        print(f"After approval - Unpaid leave: {balance.unpaid_leave}")
        
        # Check that balance doesn't go negative
        assert balance.sick_leave_balance >= 0, "Sick leave balance should not be negative"
        assert balance.sick_leave_used == 3.0, "Should use all available sick leave"
        assert balance.unpaid_leave == 2.0, "Should add excess to unpaid leave"
        
        print("✅ Leave approval correctly prevented negative balance")
    
    # Test 3: Test fix_negative_balances method
    print("\n📝 Test 3: Testing fix_negative_balances method...")
    
    # Manually create a negative balance scenario
    balance.sick_leave_used = 5.0  # More than allocated
    balance.save()
    
    print(f"Before fix - SL balance: {balance.sick_leave_balance}")
    assert balance.sick_leave_balance < 0, "Should have negative balance"
    
    # Fix negative balances
    fixed = balance.fix_negative_balances()
    
    print(f"After fix - SL balance: {balance.sick_leave_balance}")
    print(f"After fix - Unpaid leave: {balance.unpaid_leave}")
    
    assert fixed == True, "Should report that balances were fixed"
    assert balance.sick_leave_balance >= 0, "Should fix negative balance"
    assert balance.unpaid_leave >= 2.0, "Should add excess to unpaid leave"
    
    print("✅ fix_negative_balances method works correctly")
    
    # Test 4: Test that zero balance prevents application without LOP
    print("\n📝 Test 4: Testing zero balance scenario...")
    
    # Reset balance to zero
    balance.sick_leave_used = balance.sick_leave_allocated
    balance.unpaid_leave = 0
    balance.save()
    
    zero_balance_request = LeaveRequest(
        employee=employee,
        leave_type='SL',
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=12),
        duration='FULL',
        reason='Test zero balance'
    )
    
    validation = zero_balance_request.validate_leave_application()
    
    assert validation['available_balance'] == 0, "Should show zero balance"
    assert validation['will_be_lop'] == True, "Should require LOP"
    assert validation['shortfall'] == 3.0, "All days should be shortfall"
    
    print("✅ Zero balance correctly requires LOP confirmation")
    
    print("\n🎉 All tests passed! Negative balance prevention is working correctly.")
    
    # Cleanup
    try:
        user.delete()
        employee.delete()
        balance.delete()
        location.delete()
        company.delete()
        print("✅ Cleanup completed")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

if __name__ == "__main__":
    test_negative_balance_prevention()