#!/usr/bin/env python3
"""
Debug script to test the exact same flow as the web interface
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, Payslip
from core.utils import generate_payslip_pdf_with_generator

def debug_web_payslip_generation():
    """Debug the exact same flow as the web interface"""
    print("=== DEBUGGING WEB PAYSLIP GENERATION FLOW ===\n")
    
    # Get the same payslip that would be used in web interface
    payslip = Payslip.objects.select_related(
        'employee', 'employee__user', 'employee__company', 'employee__location'
    ).first()
    
    if not payslip:
        print("No payslips found in database.")
        return
    
    print(f"Testing with payslip for: {payslip.employee.user.get_full_name()}")
    print(f"Company: {payslip.employee.company.name}")
    print(f"Month: {payslip.month}")
    print(f"Employee Location: {payslip.employee.location}")
    print(f"Employee Location Currency: {payslip.employee.location.currency if payslip.employee.location else 'N/A'}")
    
    # Test the exact function call that the web interface makes
    try:
        print("\n=== CALLING generate_payslip_pdf_with_generator ===")
        result = generate_payslip_pdf_with_generator(payslip, output_dir="media/payslips")
        print(f"Function returned: {result}")
        
        if result:
            print("✅ SUCCESS: Function returned True")
            print(f"PDF file saved to: {payslip.pdf_file.name if payslip.pdf_file else 'No file saved'}")
        else:
            print("❌ FAILURE: Function returned False")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_web_payslip_generation()