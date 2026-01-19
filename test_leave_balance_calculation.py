"""
Test script to verify leave balance calculation logic
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveBalance

print("=" * 70)
print("LEAVE BALANCE CALCULATION TEST")
print("=" * 70)

# Find Saeed Syed or similar employee
employees = Employee.objects.filter(
    user__first_name__icontains='saeed'
).select_related('user')

if not employees.exists():
    # Get any employee with leave balance
    employees = Employee.objects.filter(is_active=True).select_related('user')[:5]

for emp in employees:
    print(f"\n👤 Employee: {emp.user.get_full_name()}")
    print("-" * 50)
    
    try:
        balance = emp.leave_balance
        
        print(f"📊 CASUAL LEAVE:")
        print(f"   Allocated: {balance.casual_leave_allocated}")
        print(f"   Used: {balance.casual_leave_used}")
        print(f"   Balance (calculated): {balance.casual_leave_balance}")
        print(f"   Balance (manual calc): {balance.casual_leave_allocated - balance.casual_leave_used}")
        
        print(f"\n🏥 SICK LEAVE:")
        print(f"   Allocated: {balance.sick_leave_allocated}")
        print(f"   Used: {balance.sick_leave_used}")
        print(f"   Balance (calculated): {balance.sick_leave_balance}")
        print(f"   Balance (manual calc): {balance.sick_leave_allocated - balance.sick_leave_used}")
        
        print(f"\n💰 UNPAID LEAVE:")
        print(f"   Total: {balance.unpaid_leave}")
        
        # Check if calculations match
        cl_match = balance.casual_leave_balance == (balance.casual_leave_allocated - balance.casual_leave_used)
        sl_match = balance.sick_leave_balance == (balance.sick_leave_allocated - balance.sick_leave_used)
        
        print(f"\n✅ VALIDATION:")
        print(f"   Casual Leave calculation correct: {cl_match}")
        print(f"   Sick Leave calculation correct: {sl_match}")
        
        if not cl_match or not sl_match:
            print("   ⚠️  CALCULATION MISMATCH DETECTED!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)