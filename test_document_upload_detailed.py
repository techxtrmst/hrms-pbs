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
import tempfile
from PIL import Image
import io

def create_test_image():
    """Create a simple test image file"""
    image = Image.new('RGB', (100, 100), color='red')
    img_io = io.BytesIO()
    image.save(img_io, format='JPEG')
    img_io.seek(0)
    return SimpleUploadedFile(
        name='test_image.jpg',
        content=img_io.read(),
        content_type='image/jpeg'
    )

def test_document_upload_detailed():
    print("🔍 DETAILED DOCUMENT UPLOAD TEST")
    print("=" * 50)
    
    # Get a test employee
    employees = Employee.objects.all()
    if not employees.exists():
        print("❌ No employees found for testing")
        return
    
    employee = employees.first()
    user = employee.user
    
    print(f"👤 Testing with employee: {user.email}")
    print(f"🏢 Company: {employee.company.name}")
    print(f"🔑 User role: {user.role}")
    
    # Check if EmployeeIDProof exists
    id_proofs, created = EmployeeIDProof.objects.get_or_create(employee=employee)
    if created:
        print("✅ Created EmployeeIDProof record")
    else:
        print("✅ EmployeeIDProof record exists")
    
    # Test with Django test client
    client = Client()
    
    # Login as the employee
    login_success = client.force_login(user)
    print(f"🔐 Login successful: {login_success is None}")  # force_login returns None on success
    
    # Test GET request to profile page
    profile_url = reverse('employee_profile')
    print(f"📄 Profile URL: {profile_url}")
    
    response = client.get(profile_url, HTTP_HOST='localhost')
    print(f"📊 GET Response status: {response.status_code}")
    
    content = ""
    if response.status_code == 200:
        print("✅ Profile page loads successfully")
        
        # Check if form exists in response
        content = response.content.decode('utf-8')
        if 'document-upload-form' in content:
            print("✅ Document upload form found in page")
        else:
            print("❌ Document upload form NOT found in page")
            
        if 'aadhar_front' in content:
            print("✅ Aadhar front input found")
        else:
            print("❌ Aadhar front input NOT found")
    else:
        print(f"❌ Profile page failed to load: {response.status_code}")
        content = response.content.decode('utf-8')
        print(f"Response content: {content[:500]}")
    
    # Test file upload
    print("\n📤 Testing file upload...")
    
    test_image = create_test_image()
    
    upload_data = {
        'aadhar_front': test_image,
    }
    
    response = client.post(profile_url, upload_data, follow=True, HTTP_HOST='localhost')
    print(f"📊 POST Response status: {response.status_code}")
    
    # Refresh the id_proofs object
    id_proofs.refresh_from_db()
    
    if id_proofs.aadhar_front:
        print("✅ File uploaded successfully!")
        print(f"📁 File path: {id_proofs.aadhar_front.url}")
        
        # Check if file actually exists
        file_path = id_proofs.aadhar_front.path
        if os.path.exists(file_path):
            print("✅ File exists on disk")
            print(f"📏 File size: {os.path.getsize(file_path)} bytes")
        else:
            print("❌ File does NOT exist on disk")
    else:
        print("❌ File upload failed")
        
        # Check for any error messages
        if hasattr(response, 'context') and response.context:
            messages = list(response.context.get('messages', []))
            if messages:
                print("📝 Messages:")
                for message in messages:
                    print(f"   - {message}")
    
    print("\n" + "=" * 50)
    print("🔧 SUMMARY:")
    print(f"   Profile page accessible: {'✅' if response.status_code == 200 else '❌'}")
    print(f"   Upload form present: {'✅' if 'document-upload-form' in content else '❌'}")
    print(f"   File upload working: {'✅' if id_proofs.aadhar_front else '❌'}")
    print("=" * 50)

if __name__ == '__main__':
    test_document_upload_detailed()