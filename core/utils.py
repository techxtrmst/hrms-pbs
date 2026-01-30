# PDF Utility for Payslip Generation
import io
import os
from django.core.files.base import ContentFile
from django.template.loader import render_to_string, get_template
from xhtml2pdf import pisa
from employees.payroll_utils import num2words_flexible



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
        name_upper = company.name.upper()
        if company.location == "INDIA":
            return "Asia/Kolkata"
        elif company.location == "BOTH" or "SOFTSTANDARD" in name_upper:
            # For BOTH (Softstandard), default to India if unknown
            return "Asia/Kolkata"
        elif "BLUEBIX" in name_upper:
            # Bluebix often has Indian employees even if primary location is US
            # Default to India unless a specific US office is set on profile (handled in Step 1)
            return "Asia/Kolkata"
        elif company.location == "US":
            return "America/New_York"
        
    # 3. Final Fallback
    return "Asia/Kolkata"


def generate_payslip_pdf_with_generator(payslip_instance, output_dir="media/payslips"):
    """
    Generate payslip PDF using the standard Django template: employees/templates/employees/payslip_pdf.html
    This replaces the previous PayslipGenerator logic.
    """
    
    try:
        from weasyprint import HTML
        
        # Prepare context data for the template
        employee = payslip_instance.employee
        company = employee.company
        
        # Determine branding details (name and logo logic is mostly in the template or requires branding dict)
        company_name = company.name.upper()
        branding_name = 'PETABYTZ TECHNOLOGY SERVICES PVT LTD'
        
        if 'SOFTSTANDARD' in company_name or 'SOFT STANDARD' in company_name:
            branding_name = 'SOFTSTANDARD SOLUTIONS'
        elif 'BLUEBIX' in company_name:
            branding_name = 'BLUEBIX TECHNOLOGY SERVICES PVT LTD'

        branding = {'name': branding_name}
        
        # Calculate Net Salary in Words
        currency = "INR"
        currency_name = "Rupees"
        if employee.location:
            currency = employee.location.currency or "INR"
            if currency == "USD":
                currency_name = "Dollars"
            elif currency == "BDT":
                currency_name = "Taka"
                
        net_salary_words = num2words_flexible(payslip_instance.net_salary, currency_name)
        
        context = {
            'payslip': payslip_instance,
            'company': company,
            'branding': branding,
            'net_salary_words': net_salary_words,
            'currency': currency,
        }
        
        # Render HTML from the Django template
        html_content = render_to_string('employees/payslip_pdf.html', context)
        
        # Generate PDF in memory
        pdf_buffer = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        
        # Generate Filename
        month_str = payslip_instance.month.strftime('%B-%Y')
        emp_name = employee.user.get_full_name().replace(' ', '_')
        pdf_filename = f"{emp_name}-Payslip_{month_str}.pdf"
        
        # Save to model
        payslip_instance.pdf_file.save(pdf_filename, ContentFile(pdf_buffer.getvalue()), save=True)
        
        return True
        
    except Exception as e:
        print(f"Payslip PDF generation error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
