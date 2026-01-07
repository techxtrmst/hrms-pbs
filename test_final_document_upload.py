#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, EmployeeIDProof
from accounts.models import User
from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io

def create_test_image(name="test_image.jpg"):
    """Create a simple test image file"""
    image = Image.new('RGB', (100, 100), color='red')
    img_io = io.BytesIO()
    image.save(img_io, format='JPEG')
    img_io.seek(0)
    return SimpleUploadedFile(
        name=name,
        content=img_io.read(),
        content_type='image/jpeg'
    )

def test_complete_document_upload():
    print("🔍 COMPREHENSIVE DOCUMENT UPLOAD TEST")
    print("=" * 60)
    
    # Get test employees
    employees = Employee.objects.all()[:3]  # Test with first 3 employees
    
    if not employees.exists():
        print("❌ No employees found for testing")
        return
    
    client = Client()
    
    for i, employee in enumerate(employees, 1):
        print(f"\n👤 Testing Employee {i}: {employee.user.email}")
        print(f"   Role: {employee.user.role}")
        print(f"   Company: {employee.company.name}")
        
        # Ensure EmployeeIDProof exists
        id_proofs, created = EmployeeIDProof.objects.get_or_create(employee=employee)
        if created:
            print("   ✅ Created EmployeeIDProof record")
        
        # Login as employee
        client.force_login(employee.user)
        
        # Test profile page access
        profile_url = reverse('employee_profile')
        response = client.get(profile_url, HTTP_HOST='localhost')
        
        if response.status_code == 200:
            print("   ✅ Profile page accessible")
            
            # Test file upload for each document type
            test_files = {
                'aadhar_front': create_test_image(f'aadhar_front_{i}.jpg'),
                'aadhar_back': create_test_image(f'aadhar_back_{i}.jpg'),
                'pan_card': create_test_image(f'pan_card_{i}.jpg'),
            }
            
            for doc_type, test_file in test_files.items():
                print(f"   📤 Testing {doc_type} upload...")
                
                upload_data = {doc_type: test_file}
                response = client.post(profile_url, upload_data, follow=True, HTTP_HOST='localhost')
                
                # Refresh the id_proofs object
                id_proofs.refresh_from_db()
                
                # Check if file was uploaded
                uploaded_file = getattr(id_proofs, doc_type)
                if uploaded_file:
                    print(f"      ✅ {doc_type} uploaded successfully")
                    print(f"      📁 Path: {uploaded_file.url}")
                    
                    # Check if file exists on disk
                    if os.path.exists(uploaded_file.path):
                        print(f"      ✅ File exists on disk ({os.path.getsize(uploaded_file.path)} bytes)")
                    else:
                        print(f"      ❌ File missing on disk")
                else:
                    print(f"      ❌ {doc_type} upload failed")
        else:
            print(f"   ❌ Profile page failed: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    
    # Count total uploaded documents
    total_docs = 0
    for employee in employees:
        try:
            id_proofs = employee.id_proofs
            if id_proofs.aadhar_front:
                total_docs += 1
            if id_proofs.aadhar_back:
                total_docs += 1
            if id_proofs.pan_card:
                total_docs += 1
        except EmployeeIDProof.DoesNotExist:
            pass
    
    print(f"✅ Total documents uploaded: {total_docs}")
    print(f"✅ Employees tested: {len(employees)}")
    print(f"✅ Expected documents: {len(employees) * 3}")
    
    success_rate = (total_docs / (len(employees) * 3)) * 100 if employees else 0
    print(f"📈 Success rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 DOCUMENT UPLOAD SYSTEM IS WORKING PERFECTLY!")
    elif success_rate >= 70:
        print("⚠️ Document upload system is mostly working")
    else:
        print("❌ Document upload system needs attention")
    
    print("=" * 60)

if __name__ == '__main__':
    test_complete_document_upload()