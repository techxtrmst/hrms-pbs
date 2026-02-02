# PDF Utility for Payslip Generation
import io
import logging

import pytz
from django.core.files.base import ContentFile
from django.template.loader import get_template
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

# Check if PayslipGenerator is available
try:
    from payslip_generator import PayslipGenerator

    PAYSLIP_GENERATOR_AVAILABLE = True
except ImportError:
    PayslipGenerator = None
    PAYSLIP_GENERATOR_AVAILABLE = False

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


def generate_payslip_pdf(payslip_instance, output_dir="media/payslips"):
    """
    Generate payslip PDF using the PayslipGenerator class from payslip_generator.py
    """

    if not PAYSLIP_GENERATOR_AVAILABLE:
        logger.error(
            "PayslipGenerator is required but not available. Please ensure payslip_generator.py is properly installed."
        )
        raise ImportError("PayslipGenerator is not available. Cannot generate payslip.")

    try:
        # Prepare employee data for PayslipGenerator
        employee = payslip_instance.employee
        company = employee.company

        # Determine branding details
        company_name = company.name.upper()
        branding_name = "PETABYTZ TECHNOLOGY SERVICES PVT LTD"

        if "SOFTSTANDARD" in company_name or "SOFT STANDARD" in company_name:
            branding_name = "SOFTSTANDARD SOLUTIONS"
        elif "BLUEBIX" in company_name:
            branding_name = "BLUEBIX TECHNOLOGY SERVICES PVT LTD"

        # Get currency information
        currency = "INR"
        if employee.location:
            currency = employee.location.currency or "INR"

        # Prepare earnings data (Section A)
        earnings = []
        if payslip_instance.basic > 0:
            earnings.append({"name": "Basic", "amount": float(payslip_instance.basic)})
        if payslip_instance.hra > 0:
            earnings.append({"name": "HRA", "amount": float(payslip_instance.hra)})
        if payslip_instance.lta > 0:
            earnings.append({"name": "Conveyance Allowance", "amount": float(payslip_instance.lta)})
        if payslip_instance.other_allowance > 0:
            earnings.append({"name": "Other Allowance", "amount": float(payslip_instance.other_allowance)})
        if payslip_instance.conveyance_allowance > 0:
            earnings.append({"name": "Conveyance Allowance", "amount": float(payslip_instance.conveyance_allowance)})
        if payslip_instance.special_allowance > 0:
            earnings.append({"name": "Special Allowance", "amount": float(payslip_instance.special_allowance)})

        # Prepare contributions data (Section B - PF Employee contributions)
        contributions = []
        if payslip_instance.employee_pf > 0:
            contributions.append({"name": "PF Employee", "amount": float(payslip_instance.employee_pf)})

        # Prepare deductions data (Section C - Taxes & Deductions)
        deductions = []
        if payslip_instance.professional_tax > 0:
            deductions.append({"name": "Professional Tax", "amount": float(payslip_instance.professional_tax)})

        # Check if there are additional deduction fields (TDS, LOP, etc.)
        if hasattr(payslip_instance, "tds") and payslip_instance.tds > 0:
            deductions.append({"name": "TDS", "amount": float(payslip_instance.tds)})
        if hasattr(payslip_instance, "lop_deduction") and payslip_instance.lop_deduction > 0:
            deductions.append({"name": "LOP Deduction", "amount": float(payslip_instance.lop_deduction)})

        # Determine logo URL based on company
        logo_url = None
        if "PETABYTZ" in company_name or "PETABYTES" in company_name:
            logo_url = "https://petabytz.com/images/logo/logo.png"
        elif "BLUEBIX" in company_name:
            logo_url = "https://petabytz.com/images/logo/logo.png"  # Using Petabytz logo for Bluebix as requested
        elif "SOFTSTANDARD" in company_name or "SOFT STANDARD" in company_name:
            logo_url = "https://softstandard.com/wp-content/uploads/2016/05/logo.jpg"

        # Prepare employee data dictionary
        employee_data = {
            "name": employee.user.get_full_name(),
            "employee_id": employee.badge_id or str(employee.id),
            "date_joined": employee.date_of_joining.strftime("%d-%m-%Y") if employee.date_of_joining else "N/A",
            "department": employee.department or "N/A",
            "designation": employee.designation or "N/A",
            "payment_mode": "Bank Transfer",
            "bank_name": employee.bank_name or "N/A",
            "bank_ifsc": employee.ifsc_code or "N/A",
            "bank_account": employee.account_number or "N/A",
            "uan": employee.uan or "N/A",
            "pan_number": employee.pan_number or "N/A",
            "payable_units": "30 Days",  # This could be calculated based on worked days
            "company_name": branding_name,
            "company_address": "PLOT NO 201 & 202, 1ST FLOOR, DMR CORPORATE, KAVURI HILLS RD",
            "company_city": "HYDERABAD",
            "company_state": "TELANGANA 500081",
            "currency": currency,
            "earnings": earnings,
            "contributions": contributions,
            "deductions": deductions,
            "location_obj": employee.location,  # Pass location object for currency info
            "logo_url": logo_url,  # Add logo URL for the PayslipGenerator
        }

        # Initialize PayslipGenerator
        generator = PayslipGenerator(output_dir=output_dir)

        # Generate PDF
        month_str = payslip_instance.month.strftime("%B")
        year_str = payslip_instance.month.strftime("%Y")

        pdf_path = generator.generate_payslip(employee_data, month_str, year_str)

        # Save the generated PDF to the payslip model
        with open(pdf_path, "rb") as pdf_file:
            pdf_content = pdf_file.read()

        # Generate filename for the model
        month_str = payslip_instance.month.strftime("%B-%Y")
        emp_name = employee.user.get_full_name().replace(" ", "_")
        pdf_filename = f"{emp_name}-Payslip_{month_str}.pdf"

        # Save to model
        payslip_instance.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

        logger.info(f"Payslip generated successfully with PayslipGenerator for {employee.user.get_full_name()}")
        return True

    except Exception as e:
        logger.error(
            f"PayslipGenerator failed for {payslip_instance.employee.user.get_full_name()}: {e}", exc_info=True
        )
        return False
