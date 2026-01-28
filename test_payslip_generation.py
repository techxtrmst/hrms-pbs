#!/usr/bin/env python3
"""
Test script to debug payslip generation issues
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import Employee, Payslip
from core.utils import generate_payslip_pdf_with_generator, PAYSLIP_GENERATOR_AVAILABLE

def test_payslip_generation():
    """Test payslip generation to identify issues"""
    print("=== TESTING PAYSLIP GENERATION ===\n")
    
    print(f"PayslipGenerator Available: {PAYSLIP_GENERATOR_AVAILABLE}")
    
    # Get a recent payslip
    payslip = Payslip.objects.select_related('employee', 'employee__user', 'employee__company', 'employee__location').first()
    
    if not payslip:
        print("No payslips found in database.")
        return
    
    print(f"Testing with payslip for: {payslip.employee.user.get_full_name()}")
    print(f"Company: {payslip.employee.company.name}")
    print(f"Month: {payslip.month}")
    
    try:
        # Test the PayslipGenerator directly
        from payslip_generator import PayslipGenerator
        
        generator = PayslipGenerator(output_dir="test_output")
        print("PayslipGenerator instance created successfully")
        
        # Test employee data preparation
        employee = payslip.employee
        company = employee.company
        
        # Prepare test data
        employee_data = {
            'name': employee.user.get_full_name(),
            'employee_id': employee.badge_id or 'N/A',
            'date_joined': employee.date_of_joining.strftime('%d %b %Y') if employee.date_of_joining else 'N/A',
            'department': employee.department or 'N/A',
            'designation': employee.designation or 'N/A',
            'payment_mode': 'Bank Transfer',
            'bank_name': employee.bank_name or 'N/A',
            'bank_ifsc': employee.ifsc_code or 'N/A',
            'bank_account': employee.account_number or 'N/A',
            'uan': employee.uan or 'N/A',
            'pan_number': getattr(employee, 'pan_number', 'N/A'),
            'payable_units': "30 Days",
            'company_name': 'PETABYTZ TECHNOLOGY SERVICES PVT LTD',
            'company_address': 'PLOT NO 201 & 202, 1ST FLOOR, DMR CORPORATE, KAVURI HILLS RD, HYDERABAD,',
            'company_city': 'TELANGANA 500081.',
            'company_state': 'HYDERABAD TELANGANA 500081',
            'company_postal_code': '',
            'earnings': [
                {'name': 'Basic', 'amount': float(payslip.basic)},
                {'name': 'HRA', 'amount': float(payslip.hra)},
            ],
            'deductions': [
                {'name': 'Professional Tax', 'amount': float(payslip.professional_tax)},
            ],
            'logo_path': 'logo (1).png',
            'currency': 'INR',
        }
        
        print("Employee data prepared successfully")
        
        # Test PDF generation
        month = payslip.month.strftime('%B')
        year = payslip.month.strftime('%Y')
        
        print(f"Attempting to generate PDF for {month} {year}")
        
        pdf_path = generator.generate_payslip(employee_data, month, year)
        print(f"PDF generated at: {pdf_path}")
        
        if os.path.exists(pdf_path):
            print(f"✅ PDF file exists and is {os.path.getsize(pdf_path)} bytes")
        else:
            print("❌ PDF file was not created")
            
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        import traceback
        traceback.print_exc()
    
    # Test the full function
    print("\n=== TESTING FULL FUNCTION ===")
    try:
        result = generate_payslip_pdf_with_generator(payslip, output_dir="test_output")
        print(f"Function result: {result}")
    except Exception as e:
        print(f"Function error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_payslip_generation()