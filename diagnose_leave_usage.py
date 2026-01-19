"""
Diagnostic script to check leave usage discrepancies
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, LeaveRequest, LeaveBalance
from django.db.models import Sum

print("=" * 80)
print("LEAVE USAGE DIAGNOSTIC REPORT")
print("=" * 80)

# Find employees with potential discrepancies
employees = Employee.objects.filter(is_active=True).select_related('user')

for emp in employees[:10]:  # Check first 10 employees
    print(f"\n👤 Employee: {emp.user.get_full_name()}")
    print("-" * 60)
    
    try:
        balance = emp.leave_balance
        
        # Get actual approved leave requests
        approved_cl_requests = LeaveRequest.objects.filter(
            employee=emp,
            status='APPROVED',
            leave_type='CL'
        )
        approved_cl = sum(req.total_days for req in approved_cl_requests)
        
        approved_sl_requests = LeaveRequest.objects.filter(
            employee=emp,
            status='APPROVED',
            leave_type='SL'
        )
        approved_sl = sum(req.total_days for req in approved_sl_requests)
        
        print(f"📊 CASUAL LEAVE:")
        print(f"   Allocated: {balance.casual_leave_allocated}")
        print(f"   Used (in balance): {balance.casual_leave_used}")
        print(f"   Used (actual approved): {approved_cl}")
        print(f"   Balance (calculated): {balance.casual_leave_balance}")
        print(f"   Balance (should be): {balance.casual_leave_allocated - approved_cl}")
        
        cl_discrepancy = balance.casual_leave_used != approved_cl
        if cl_discrepancy:
            print(f"   ⚠️  DISCREPANCY: Used field ({balance.casual_leave_used}) != Approved requests ({approved_cl})")
        
        print(f"\n🏥 SICK LEAVE:")
        print(f"   Allocated: {balance.sick_leave_allocated}")
        print(f"   Used (in balance): {balance.sick_leave_used}")
        print(f"   Used (actual approved): {approved_sl}")
        print(f"   Balance (calculated): {balance.sick_leave_balance}")
        print(f"   Balance (should be): {balance.sick_leave_allocated - approved_sl}")
        
        sl_discrepancy = balance.sick_leave_used != approved_sl
        if sl_discrepancy:
            print(f"   ⚠️  DISCREPANCY: Used field ({balance.sick_leave_used}) != Approved requests ({approved_sl})")
        
        # Show recent leave requests
        recent_leaves = LeaveRequest.objects.filter(employee=emp, status='APPROVED').order_by('-approved_at')[:5]
        if recent_leaves:
            print(f"\n📋 RECENT APPROVED LEAVES:")
            for leave in recent_leaves:
                print(f"   {leave.get_leave_type_display()}: {leave.total_days} days ({leave.start_date} to {leave.end_date})")
        
        if cl_discrepancy or sl_discrepancy:
            print(f"\n🔧 SUGGESTED FIX:")
            print(f"   Set casual_leave_used = {approved_cl}")
            print(f"   Set sick_leave_used = {approved_sl}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)