# PDF Utility for Payslip Generation
import io
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.core.files.base import ContentFile

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

