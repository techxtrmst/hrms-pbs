"""
Utility functions for sending birthday and anniversary emails
Supports company-specific email configuration
"""

from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_company_email_connection(company):
    """
    Get email connection for a specific company

    Args:
        company: Company model instance

    Returns:
        EmailBackend connection or None if company email not configured
    """
    # Check if company has email configuration
    if company.hr_email and company.hr_email_password:
        # Use company-specific email settings
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host="smtp.office365.com",  # Office 365 for all companies
            port=587,
            use_tls=True,
            username=company.hr_email,
            password=company.hr_email_password,
            fail_silently=False,
        )
        return connection
    else:
        # Fall back to default Django email settings
        return get_connection()


def send_birthday_email(employee):
    """
    Send individual birthday email to an employee using company-specific email

    Args:
        employee: Employee model instance

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if employee has email
        if not employee.user.email:
            logger.warning(
                f"Employee {employee.user.get_full_name()} has no email address"
            )
            return False

        # Get company-specific email connection
        connection = get_company_email_connection(employee.company)

        # Determine from email
        if employee.company.hr_email:
            from_name = employee.company.hr_email_name or f"{employee.company.name} HR"
            from_email = f"{from_name} <{employee.company.hr_email}>"
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        # Prepare context for email template
        context = {
            "employee_name": employee.user.get_full_name(),
            "company_name": employee.company.name,
        }

        # Render HTML email
        html_content = render_to_string("core/emails/birthday_email.html", context)

        # Create email
        subject = f"🎉 Happy Birthday {employee.user.first_name}!"
        recipient_list = [employee.user.email]

        # Send email
        email = EmailMultiAlternatives(
            subject, "", from_email, recipient_list, connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(
            f"Birthday email sent to {employee.user.get_full_name()} ({employee.user.email}) from {from_email}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to send birthday email to {employee.user.get_full_name()}: {str(e)}"
        )
        return False


def send_anniversary_email(employee, years):
    """
    Send individual work anniversary email to an employee using company-specific email

    Args:
        employee: Employee model instance
        years: Number of years of service

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if employee has email
        if not employee.user.email:
            logger.warning(
                f"Employee {employee.user.get_full_name()} has no email address"
            )
            return False

        # Get company-specific email connection
        connection = get_company_email_connection(employee.company)

        # Determine from email
        if employee.company.hr_email:
            from_name = employee.company.hr_email_name or f"{employee.company.name} HR"
            from_email = f"{from_name} <{employee.company.hr_email}>"
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        # Prepare context for email template
        context = {
            "employee_name": employee.user.get_full_name(),
            "company_name": employee.company.name,
            "years_of_service": years,
        }

        # Render HTML email
        html_content = render_to_string("core/emails/anniversary_email.html", context)

        # Create email
        subject = f"🎊 Congratulations on {years} Year{'s' if years != 1 else ''} with {employee.company.name}!"
        recipient_list = [employee.user.email]

        # Send email
        email = EmailMultiAlternatives(
            subject, "", from_email, recipient_list, connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(
            f"Anniversary email sent to {employee.user.get_full_name()} ({employee.user.email}) from {from_email} - {years} years"
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to send anniversary email to {employee.user.get_full_name()}: {str(e)}"
        )
        return False


def send_birthday_announcement(employee, company_employees):
    """
    Send birthday announcement to all employees in the company using company-specific email

    Args:
        employee: Employee model instance (birthday person)
        company_employees: QuerySet of all employees in the company

    Returns:
        int: Number of emails sent successfully
    """
    try:
        # Get company-specific email connection
        connection = get_company_email_connection(employee.company)

        # Determine from email
        if employee.company.hr_email:
            from_name = employee.company.hr_email_name or f"{employee.company.name} HR"
            from_email = f"{from_name} <{employee.company.hr_email}>"
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        # Prepare context for email template
        context = {
            "employee_name": employee.user.get_full_name(),
            "employee_first_name": employee.user.first_name,
            "department": employee.department,
            "designation": employee.designation,
            "company_name": employee.company.name,
        }

        # Render HTML email
        html_content = render_to_string(
            "core/emails/birthday_announcement.html", context
        )

        # Create email
        subject = f"🎂 {employee.user.first_name}'s Birthday Today!"

        # Get all employee emails (excluding the birthday person and those without email)
        recipient_list = [
            emp.user.email
            for emp in company_employees
            if emp.user.email and emp.id != employee.id
        ]

        if not recipient_list:
            logger.warning(
                f"No recipients found for birthday announcement of {employee.user.get_full_name()}"
            )
            return 0

        # Send email
        email = EmailMultiAlternatives(
            subject, "", from_email, recipient_list, connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(
            f"Birthday announcement sent to {len(recipient_list)} employees for {employee.user.get_full_name()} from {from_email}"
        )
        return len(recipient_list)

    except Exception as e:
        logger.error(
            f"Failed to send birthday announcement for {employee.user.get_full_name()}: {str(e)}"
        )
        return 0


def send_anniversary_announcement(employee, years, company_employees):
    """
    Send work anniversary announcement to all employees in the company using company-specific email

    Args:
        employee: Employee model instance (anniversary person)
        years: Number of years of service
        company_employees: QuerySet of all employees in the company

    Returns:
        int: Number of emails sent successfully
    """
    try:
        # Get company-specific email connection
        connection = get_company_email_connection(employee.company)

        # Determine from email
        if employee.company.hr_email:
            from_name = employee.company.hr_email_name or f"{employee.company.name} HR"
            from_email = f"{from_name} <{employee.company.hr_email}>"
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        # Prepare context for email template
        context = {
            "employee_name": employee.user.get_full_name(),
            "employee_first_name": employee.user.first_name,
            "department": employee.department,
            "designation": employee.designation,
            "company_name": employee.company.name,
            "years_of_service": years,
        }

        # Render HTML email
        html_content = render_to_string(
            "core/emails/anniversary_announcement.html", context
        )

        # Create email
        subject = f"🏆 {employee.user.first_name}'s {years} Year Work Anniversary!"

        # Get all employee emails (excluding the anniversary person and those without email)
        recipient_list = [
            emp.user.email
            for emp in company_employees
            if emp.user.email and emp.id != employee.id
        ]

        if not recipient_list:
            logger.warning(
                f"No recipients found for anniversary announcement of {employee.user.get_full_name()}"
            )
            return 0

        # Send email
        email = EmailMultiAlternatives(
            subject, "", from_email, recipient_list, connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(
            f"Anniversary announcement sent to {len(recipient_list)} employees for {employee.user.get_full_name()} from {from_email} - {years} years"
        )
        return len(recipient_list)

    except Exception as e:
        logger.error(
            f"Failed to send anniversary announcement for {employee.user.get_full_name()}: {str(e)}"
        )
        return 0


def send_probation_completion_email(employee):
    """
    Send probation completion email to an employee using company-specific email
    Sent when employee completes 3 months from joining date

    Args:
        employee: Employee model instance

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if employee has email
        if not employee.user.email:
            logger.warning(
                f"Employee {employee.user.get_full_name()} has no email address"
            )
            return False

        # Get company-specific email connection
        connection = get_company_email_connection(employee.company)

        # Determine from email
        if employee.company.hr_email:
            from_name = employee.company.hr_email_name or f"{employee.company.name} HR"
            from_email = f"{from_name} <{employee.company.hr_email}>"
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        # Prepare context for email template
        context = {
            "employee_name": employee.user.get_full_name(),
            "company_name": employee.company.name,
        }

        # Render HTML email
        html_content = render_to_string(
            "core/emails/probation_completion_email.html", context
        )

        # Create email
        subject = f"🏆 Congratulations! Probation Period Completed - Welcome to {employee.company.name}!"
        recipient_list = [employee.user.email]

        # Send email
        email = EmailMultiAlternatives(
            subject, "", from_email, recipient_list, connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(
            f"Probation completion email sent to {employee.user.get_full_name()} ({employee.user.email}) from {from_email}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to send probation completion email to {employee.user.get_full_name()}: {str(e)}"
        )
        return False


def send_leave_request_notification(leave_request):
    """
    Send leave request notification to reporting manager and HR/Admin

    Args:
        leave_request: LeaveRequest model instance

    Returns:
        dict: Status of emails sent {'manager': bool, 'hr': bool}
    """
    result = {"manager": False, "hr": False}

    try:
        employee = leave_request.employee
        company = employee.company

        # Get company-specific email connection
        connection = get_company_email_connection(company)

        # Determine from email
        if company.hr_email:
            from_name = company.hr_email_name or f"{company.name} HR"
            from_email = f"{from_name} <{company.hr_email}>"
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        # Prepare context for email template
        context = {
            "employee_name": employee.user.get_full_name(),
            "employee_id": employee.badge_id or "N/A",
            "department": employee.department,
            "designation": employee.designation,
            "leave_type": leave_request.get_leave_type_display(),
            "start_date": leave_request.start_date.strftime("%d %B %Y"),
            "end_date": leave_request.end_date.strftime("%d %B %Y"),
            "duration": leave_request.get_duration_display(),
            "total_days": leave_request.total_days,
            "reason": leave_request.reason,
            "company_name": company.name,
            "request_date": leave_request.created_at.strftime("%d %B %Y at %I:%M %p"),
        }

        # Render HTML email
        html_content = render_to_string(
            "core/emails/leave_request_notification.html", context
        )

        # Create email subject
        subject = f"Leave Application: {employee.user.get_full_name()} - {leave_request.get_leave_type_display()}"

        # Send to Reporting Manager
        if employee.manager and employee.manager.email:
            try:
                email = EmailMultiAlternatives(
                    subject,
                    "",
                    from_email,
                    [employee.manager.email],
                    connection=connection,
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                result["manager"] = True
                logger.info(
                    f"Leave request notification sent to manager {employee.manager.email} for {employee.user.get_full_name()}"
                )
            except Exception as e:
                logger.error(f"Failed to send leave request email to manager: {str(e)}")

        # Send to HR/Admin (company HR email)
        if company.hr_email:
            try:
                email = EmailMultiAlternatives(
                    subject, "", from_email, [company.hr_email], connection=connection
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                result["hr"] = True
                logger.info(
                    f"Leave request notification sent to HR {company.hr_email} for {employee.user.get_full_name()}"
                )
            except Exception as e:
                logger.error(f"Failed to send leave request email to HR: {str(e)}")

        return result

    except Exception as e:
        logger.error(f"Failed to send leave request notifications: {str(e)}")
        return result


def send_regularization_request_notification(regularization_request):
    """
    Send regularization request notification to reporting manager and HR/Admin

    Args:
        regularization_request: RegularizationRequest model instance

    Returns:
        dict: Status of emails sent {'manager': bool, 'hr': bool}
    """
    result = {"manager": False, "hr": False}

    try:
        employee = regularization_request.employee
        company = employee.company

        # Get company-specific email connection
        connection = get_company_email_connection(company)

        # Determine from email
        if company.hr_email:
            from_name = company.hr_email_name or f"{company.name} HR"
            from_email = f"{from_name} <{company.hr_email}>"
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        # Prepare context for email template
        context = {
            "employee_name": employee.user.get_full_name(),
            "employee_id": employee.badge_id or "N/A",
            "department": employee.department,
            "designation": employee.designation,
            "date": regularization_request.date.strftime("%d %B %Y"),
            "check_in": regularization_request.check_in.strftime("%I:%M %p")
            if regularization_request.check_in
            else "Not specified",
            "check_out": regularization_request.check_out.strftime("%I:%M %p")
            if regularization_request.check_out
            else "Not specified",
            "reason": regularization_request.reason,
            "company_name": company.name,
            "request_date": regularization_request.created_at.strftime(
                "%d %B %Y at %I:%M %p"
            ),
        }

        # Render HTML email
        html_content = render_to_string(
            "core/emails/regularization_request_notification.html", context
        )

        # Create email subject
        subject = (
            f"⏰ Attendance Regularization Request from {employee.user.get_full_name()}"
        )

        # Send to Reporting Manager
        if employee.manager and employee.manager.email:
            try:
                email = EmailMultiAlternatives(
                    subject,
                    "",
                    from_email,
                    [employee.manager.email],
                    connection=connection,
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                result["manager"] = True
                logger.info(
                    f"Regularization request notification sent to manager {employee.manager.email} for {employee.user.get_full_name()}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send regularization request email to manager: {str(e)}"
                )

        # Send to HR/Admin (company HR email)
        if company.hr_email:
            try:
                email = EmailMultiAlternatives(
                    subject, "", from_email, [company.hr_email], connection=connection
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                result["hr"] = True
                logger.info(
                    f"Regularization request notification sent to HR {company.hr_email} for {employee.user.get_full_name()}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send regularization request email to HR: {str(e)}"
                )

        return result

    except Exception as e:
        logger.error(f"Failed to send regularization request notifications: {str(e)}")
        return result
