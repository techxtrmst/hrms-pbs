#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from employees.models import Employee, EmployeeIDProof
from accounts.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
from PIL import Image
import io

def create_test_image():
    """Create a simple test image file"""
    # Create a simple 100x100 red image
    img = Image.new('RGB', (100, 100), color='red')
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    return SimpleUploadedFile("test_aadhar.jpg", img_io.getvalue(), content_type="image/jpeg")

def test_document_upload_functionality():
    print("🧪 TESTING DOCUMENT UPLOAD FUNCTIONALITY")
    print("=" * 60)
    
    # Get a test employee
    try:
        employee = Employee.objects.first()
        if not employee:
            print("❌ No employees found in database")
            return
        
        user = employee.user
        print(f"👤 Testing with employee: {user.email}")
        
        # Ensure EmployeeIDProof exists
        id_proofs, created = EmployeeIDProof.objects.get_or_create(employee=employee)
        if created:
            print("✅ Created EmployeeIDProof record")
        
        # Create test client and login
        client = Client()
        
        # Test GET request first
        print("\n📄 Testing GET request to employee profile...")
        response = client.get('/employees/profile/', follow=True)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 302:
            print("   Redirected (user not logged in)")
            
            # Try to login (this might not work without proper session setup)
            login_success = client.login(username=user.username, password='password')
            if not login_success:
                print("   ⚠️  Could not login with test client")
                print("   This is expected - manual testing required")
            else:
                print("   ✅ Logged in successfully")
                response = client.get('/employees/profile/')
                print(f"   Profile page status: {response.status_code}")
        
        # Test form structure
        print("\n🔍 Checking form structure...")
        if b'document-upload-form' in response.content:
            print("   ✅ Document upload form found")
        else:
            print("   ❌ Document upload form not found")
        
        if b'name="aadhar_front"' in response.content:
            print("   ✅ Aadhar front input found")
        else:
            print("   ❌ Aadhar front input not found")
        
        # Test file upload (this will likely fail due to authentication)
        print("\n📤 Testing file upload...")
        test_file = create_test_image()
        
        response = client.post('/employees/profile/', {
            'aadhar_front': test_file,
        }, follow=True)
        
        print(f"   Upload response status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Upload request processed")
        elif response.status_code == 302:
            print("   ⚠️  Redirected (likely due to authentication)")
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
        
        # Check if file was actually saved
        id_proofs.refresh_from_db()
        if id_proofs.aadhar_front:
            print("   ✅ File was saved to database")
        else:
            print("   ❌ File was not saved to database")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🔧 MANUAL TESTING STEPS:")
    print("1. Start the Django server: python manage.py runserver")
    print("2. Login as an employee")
    print("3. Go to Profile > Docs tab")
    print("4. Try uploading a document")
    print("5. Check browser console for JavaScript errors")
    print("6. Check Django logs for server-side errors")
    print("=" * 60)

if __name__ == '__main__':
    test_document_upload_functionality()