#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, EmployeeIDProof
from accounts.models import User

def test_document_upload():
    print("🔍 TESTING DOCUMENT UPLOAD FUNCTIONALITY")
    print("=" * 50)
    
    # Check if employees exist
    employees = Employee.objects.all()
    print(f"Total employees: {employees.count()}")
    
    if employees.count() == 0:
        print("❌ No employees found")
        return
    
    # Check EmployeeIDProof records
    for employee in employees[:3]:  # Check first 3
        try:
            id_proofs = employee.id_proofs
            print(f"\n👤 Employee: {employee.user.email}")
            print(f"   Aadhar Front: {'✅' if id_proofs.aadhar_front else '❌'}")
            print(f"   Aadhar Back: {'✅' if id_proofs.aadhar_back else '❌'}")
            print(f"   PAN Card: {'✅' if id_proofs.pan_card else '❌'}")
        except EmployeeIDProof.DoesNotExist:
            print(f"\n👤 Employee: {employee.user.email}")
            print("   ❌ No EmployeeIDProof record found")
            
            # Create the record
            id_proofs = EmployeeIDProof.objects.create(employee=employee)
            print("   ✅ Created EmployeeIDProof record")
    
    print(f"\n📁 Media Configuration:")
    from django.conf import settings
    print(f"   MEDIA_URL: {settings.MEDIA_URL}")
    print(f"   MEDIA_ROOT: {settings.MEDIA_ROOT}")
    
    # Check if media directory exists
    import os
    if os.path.exists(settings.MEDIA_ROOT):
        print(f"   ✅ Media directory exists")
    else:
        print(f"   ❌ Media directory doesn't exist")
        try:
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            print(f"   ✅ Created media directory")
        except Exception as e:
            print(f"   ❌ Failed to create media directory: {e}")
    
    print("\n" + "=" * 50)
    print("🔧 POTENTIAL ISSUES TO CHECK:")
    print("1. File upload permissions")
    print("2. JavaScript errors in browser console")
    print("3. Form submission not working")
    print("4. CSRF token issues")
    print("5. File size limits")
    print("=" * 50)

if __name__ == '__main__':
    test_document_upload()