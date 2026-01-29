# PDF Utility for Payslip Generation using WeasyPrint
import io
import os
from django.template.loader import get_template
from django.core.files.base import ContentFile
from xhtml2pdf import pisa

# Conditional import for PayslipGenerator to handle CI/CD environments
try:
    from payslip_generator import PayslipGenerator
    PAYSLIP_GENERATOR_AVAILABLE = True
except Exception as e:
    print(f"WARNING: PayslipGenerator module import failed: {e}")
    PAYSLIP_GENERATOR_AVAILABLE = False
    PayslipGenerator = None


def render_to_pdf_weasyprint(template_src, context_dict={}):
    """Render PDF using WeasyPrint - for non-payslip PDFs"""
    try:
        from weasyprint import HTML
        template = get_template(template_src)
        html = template.render(context_dict)
        result = io.BytesIO()
        HTML(string=html).write_pdf(result)
        return result.getvalue()
    except Exception as e:
        print(f"WeasyPrint PDF generation error: {e}")
        return None


def render_to_pdf(template_src, context_dict={}):
    """Legacy function using xhtml2pdf (pisa)"""
    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None


def save_pdf_to_model(model_instance, template_src, context_dict, filename):
    pdf_content = render_to_pdf(template_src, context_dict)
    if pdf_content:
        model_instance.pdf_file.save(filename, ContentFile(pdf_content), save=True)
        return True
    return False


def get_user_timezone(user, company=None):
    """
    Resolve the correct timezone for a user based on their profile or company location.
    """
    # 1. Try Employee Profile Location
    if user and user.is_authenticated and hasattr(user, "employee_profile"):
        employee = user.employee_profile
        if employee.location and employee.location.timezone:
            return employee.location.timezone

    # 2. Try Company Settings Fallback
    if company:
        if company.location == "INDIA":
            return "Asia/Kolkata"
        elif company.location == "US":
            return "America/New_York"
        elif company.location == "BOTH":
            # For BOTH (Softstandard), default to India if unknown
            # But we could also try to guess from company name if needed
            return "Asia/Kolkata"
        
    # 3. Final Fallback
    return "Asia/Kolkata"


def generate_payslip_pdf_with_generator(payslip_instance, output_dir="media/payslips"):
    """
    Generate payslip PDF using the new PayslipGenerator class
    Returns the file path of the generated PDF
    """
    
    # Check if PayslipGenerator is available
    if not PAYSLIP_GENERATOR_AVAILABLE:
        raise ImportError("PayslipGenerator is not available due to missing dependencies (weasyprint). Falling back to alternative PDF generation.")
    
    try:
        # Create PayslipGenerator instance
        generator = PayslipGenerator(output_dir=output_dir)
        
        # Prepare employee data for the generator
        employee = payslip_instance.employee
        company = employee.company
        
        # Determine logo and company details based on company name
        company_name = company.name.upper()
        
        # Standard address for all companies
        company_address_line1 = 'PLOT NO 201 & 202, 1ST FLOOR, DMR CORPORATE, KAVURI HILLS RD, HYDERABAD,'
        company_city_line = 'TELANGANA 500081.'
        company_state_line = 'HYDERABAD TELANGANA 500081'
        
        if 'SOFTSTANDARD' in company_name or 'SOFT STANDARD' in company_name:
            # SoftStandard company details
            logo_path = 'https://softstandard.com/wp-content/uploads/2016/05/logo.jpg'
            company_display_name = 'SOFTSTANDARD SOLUTIONS'
        elif 'BLUEBIX' in company_name:
            # Bluebix company details
            logo_path = 'logo (1).png'
            company_display_name = 'BLUEBIX TECHNOLOGY SERVICES PVT LTD'
        else:
            # Petabytz (and other companies) - default
            logo_path = 'logo (1).png'
            company_display_name = 'PETABYTZ TECHNOLOGY SERVICES PVT LTD'
        
        # Get month and year from payslip
        month_date = payslip_instance.month
        month = month_date.strftime('%B')
        year = month_date.strftime('%Y')
        
        # Prepare earnings data
        earnings = [
            {'name': 'Basic', 'amount': float(payslip_instance.basic)},
            {'name': 'HRA', 'amount': float(payslip_instance.hra)},
        ]
        
        # Add optional earnings if they exist - with location-specific naming
        if payslip_instance.lta > 0:
            # For India location, show as "Conveyance Allowance" instead of "LTA"
            if employee.location and employee.location.country_code == 'IN':
                earnings.append({'name': 'Conveyance Allowance', 'amount': float(payslip_instance.lta)})
            else:
                earnings.append({'name': 'LTA', 'amount': float(payslip_instance.lta)})
        if payslip_instance.other_allowance > 0:
            earnings.append({'name': 'Other Allowance', 'amount': float(payslip_instance.other_allowance)})
        if payslip_instance.conveyance_allowance > 0:
            earnings.append({'name': 'Conveyance', 'amount': float(payslip_instance.conveyance_allowance)})
        if payslip_instance.special_allowance > 0:
            earnings.append({'name': 'Special Allowance', 'amount': float(payslip_instance.special_allowance)})
        
        # Prepare deductions data
        deductions = []
        if payslip_instance.employee_pf > 0:
            deductions.append({'name': 'Provident Fund', 'amount': float(payslip_instance.employee_pf)})
        if payslip_instance.professional_tax > 0:
            deductions.append({'name': 'Professional Tax', 'amount': float(payslip_instance.professional_tax)})
        
        # Prepare employee data dictionary
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
            'payable_units': f"{payslip_instance.worked_days} Days" if hasattr(payslip_instance, 'worked_days') else "30 Days",
            'company_name': company_display_name,
            'company_address': company_address_line1,
            'company_city': company_city_line,
            'company_state': company_state_line,
            'company_postal_code': '',
            'earnings': earnings,
            'deductions': deductions,
            'logo_path': logo_path,
            'currency': employee.location.currency if employee.location else 'INR',
            'location_obj': employee.location,  # Pass location object for currency detection
        }
        
        # Generate PDF using PayslipGenerator
        pdf_path = generator.generate_payslip(employee_data, month, year)
        
        # Save the generated PDF to the model
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf_file:
                filename = os.path.basename(pdf_path)
                payslip_instance.pdf_file.save(filename, ContentFile(pdf_file.read()), save=True)
            
            # Clean up the temporary file
            os.remove(pdf_path)
            return True
        
        return False
        
    except Exception as e:
        print(f"PayslipGenerator error: {e}")
        return False
