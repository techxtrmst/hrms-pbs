# PDF Utility for Payslip Generation
import io
import logging

import pytz
from django.core.files.base import ContentFile
from django.template.loader import get_template, render_to_string
from xhtml2pdf import pisa

from employees.payroll_utils import num2words_flexible

logger = logging.getLogger(__name__)

# Common timezone abbreviation mappings to valid pytz timezones
TIMEZONE_ABBREVIATION_MAP = {
    "IST": "Asia/Kolkata",  # Indian Standard Time
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "GMT": "UTC",
    "UTC": "UTC",
    "BST": "Europe/London",
}


def normalize_timezone(tz_name, fallback="Asia/Kolkata"):
    """
    Normalize a timezone string to a valid pytz timezone.
    Handles common abbreviations like IST, EST, etc.
    """
    if not tz_name:
        return fallback

    # Check if it's already a valid pytz timezone
    try:
        pytz.timezone(tz_name)
        return tz_name
    except pytz.UnknownTimeZoneError:
        pass

    # Try to map common abbreviations
    tz_upper = tz_name.upper().strip()
    if tz_upper in TIMEZONE_ABBREVIATION_MAP:
        return TIMEZONE_ABBREVIATION_MAP[tz_upper]

    # Return fallback for unknown timezones
    return fallback


def render_to_pdf_weasyprint(template_src, context_dict=None):
    """Render PDF using WeasyPrint - for non-payslip PDFs"""
    if context_dict is None:
        context_dict = {}
    try:
        from weasyprint import HTML

        template = get_template(template_src)
        html = template.render(context_dict)
        result = io.BytesIO()
        HTML(string=html).write_pdf(result)
        return result.getvalue()
    except Exception as e:
        logger.error("WeasyPrint PDF generation error: %s", e)
        return None


def render_to_pdf(template_src, context_dict=None):
    if context_dict is None:
        context_dict = {}
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
    Returns a valid pytz timezone string.
    """
    # 1. Try Employee Profile Location
    if user and user.is_authenticated and hasattr(user, "employee_profile"):
        employee = user.employee_profile
        if employee.location and employee.location.timezone:
            # Normalize the timezone to handle abbreviations like IST
            return normalize_timezone(employee.location.timezone)

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
        branding_name = "PETABYTZ TECHNOLOGY SERVICES PVT LTD"

        if "SOFTSTANDARD" in company_name or "SOFT STANDARD" in company_name:
            branding_name = "SOFTSTANDARD SOLUTIONS"
        elif "BLUEBIX" in company_name:
            branding_name = "BLUEBIX TECHNOLOGY SERVICES PVT LTD"

        branding = {"name": branding_name}

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
            "payslip": payslip_instance,
            "company": company,
            "branding": branding,
            "net_salary_words": net_salary_words,
            "currency": currency,
        }

        # Render HTML from the Django template
        html_content = render_to_string("employees/payslip_pdf.html", context)

        # Generate PDF in memory
        pdf_buffer = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)

        # Generate Filename
        month_str = payslip_instance.month.strftime("%B-%Y")
        emp_name = employee.user.get_full_name().replace(" ", "_")
        pdf_filename = f"{emp_name}-Payslip_{month_str}.pdf"

        # Save to model
        payslip_instance.pdf_file.save(pdf_filename, ContentFile(pdf_buffer.getvalue()), save=True)

        return True

    except Exception as e:
        logger.error("Payslip PDF generation error: %s", e, exc_info=True)
        return False
