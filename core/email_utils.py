"""
Utility functions for sending birthday and anniversary emails
Supports company-specific email configuration
"""

from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.conf import settings
import logging
import environ

env = environ.Env()
logger = logging.getLogger(__name__)


def get_hr_email_connection():
    """
    Get email connection for hrms@petabytz.com with forced .env reload
    to ensure detailed password updates are picked up without server restart.
    """
    # Force reload .env
    try:
        environ.Env.read_env(settings.BASE_DIR / ".env")
    except Exception as e:
        logger.warning(f"Could not reload .env file: {e}")

    # Use EMAIL_HOST_PASSWORD (standard Django env var) with fallback to PETABYTZ_HR_EMAIL_PASSWORD
    password = env("EMAIL_HOST_PASSWORD", default=env("PETABYTZ_HR_EMAIL_PASSWORD", default=""))

    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host="smtp.office365.com",
        port=587,
        use_tls=True,
        username="hrms@petabytz.com",
        password=password,
        fail_silently=False,
    )


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
    Send individual birthday email to an employee using hrms@petabytz.com

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

        # MANDATORY: Use hrms@petabytz.com for all birthday emails
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection
        connection = get_hr_email_connection()

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
    Send individual work anniversary email to an employee using hrms@petabytz.com

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

        # MANDATORY: Use hrms@petabytz.com for all anniversary emails
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection
        connection = get_hr_email_connection()

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
    Send birthday announcement to all employees in the company using hrms@petabytz.com

    Args:
        employee: Employee model instance (birthday person)
        company_employees: QuerySet of all employees in the company

    Returns:
        int: Number of emails sent successfully
    """
    try:
        # MANDATORY: Use hrms@petabytz.com for all birthday announcements
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection
        connection = get_hr_email_connection()

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
    Send work anniversary announcement to all employees in the company using hrms@petabytz.com

    Args:
        employee: Employee model instance (anniversary person)
        years: Number of years of service
        company_employees: QuerySet of all employees in the company

    Returns:
        int: Number of emails sent successfully
    """
    try:
        # MANDATORY: Use hrms@petabytz.com for all anniversary announcements
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection
        connection = get_hr_email_connection()

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
    Send probation completion email to an employee using hrms@petabytz.com
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

        # MANDATORY: Use hrms@petabytz.com for all probation emails
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection
        connection = get_hr_email_connection()

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
    Send leave request notification to hrms@petabytz.com (MANDATORY) and reporting manager

    Args:
        leave_request: LeaveRequest model instance

    Returns:
        dict: Status of emails sent {'manager': bool, 'hr': bool}
    """
    result = {"manager": False, "hr": False}

    try:
        from datetime import datetime

        employee = leave_request.employee
        company = employee.company

        # MANDATORY: Use hrms@petabytz.com for all leave request notifications
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection using helper that reloads env
        connection = get_hr_email_connection()

        # Helper function to format dates safely
        def format_date(date_obj, format_str="%d %B %Y"):
            if isinstance(date_obj, str):
                # Try to parse string to date
                try:
                    date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()
                except:
                    return date_obj  # Return as-is if parsing fails
            return (
                date_obj.strftime(format_str)
                if hasattr(date_obj, "strftime")
                else str(date_obj)
            )

        def format_datetime(dt_obj, format_str="%d %B %Y at %I:%M %p"):
            if isinstance(dt_obj, str):
                # Try to parse string to datetime
                try:
                    dt_obj = datetime.fromisoformat(dt_obj.replace("Z", "+00:00"))
                except:
                    return dt_obj  # Return as-is if parsing fails
            return (
                dt_obj.strftime(format_str)
                if hasattr(dt_obj, "strftime")
                else str(dt_obj)
            )

        # Prepare context for email template
        context = {
            "employee_name": employee.user.get_full_name(),
            "employee_id": employee.badge_id or "N/A",
            "department": employee.department,
            "designation": employee.designation,
            "leave_type": leave_request.get_leave_type_display(),
            "start_date": format_date(leave_request.start_date),
            "end_date": format_date(leave_request.end_date),
            "duration": leave_request.get_duration_display(),
            "total_days": leave_request.total_days,
            "reason": leave_request.reason,
            "company_name": company.name,
            "request_date": format_datetime(leave_request.created_at),
        }

        # Log context for debugging
        logger.info(f"Email context: {context}")

        # Render HTML email
        try:
            html_content = render_to_string(
                "core/emails/leave_request_notification.html", context
            )
            logger.info(f"Template rendered successfully, length: {len(html_content)}")
        except Exception as e:
            logger.error(f"Failed to render email template: {str(e)}")
            import traceback

            logger.error(f"Template rendering traceback: {traceback.format_exc()}")
            # Fallback to simple HTML
            html_content = f"""
            <html>
            <body>
                <h2>Leave Request from {context["employee_name"]}</h2>
                <p><strong>Leave Type:</strong> {context["leave_type"]}</p>
                <p><strong>Duration:</strong> {context["start_date"]} to {context["end_date"]}</p>
                <p><strong>Days:</strong> {context["total_days"]}</p>
                <p><strong>Reason:</strong> {context["reason"]}</p>
            </body>
            </html>
            """

        # Create email subject
        subject = f"📋 Leave Application: {employee.user.get_full_name()} - {leave_request.get_leave_type_display()}"

        # Build recipient list - MANDATORY: hrms@petabytz.com MUST receive all leave requests
        recipients = ["hrms@petabytz.com"]

        # Add reporting manager to recipients if exists
        if employee.manager and employee.manager.email:
            recipients.append(employee.manager.email)

        # Send to all recipients (hrms@petabytz.com + manager)
        try:
            email = EmailMultiAlternatives(
                subject, "", from_email, recipients, connection=connection
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            result["hr"] = True
            if employee.manager and employee.manager.email:
                result["manager"] = True
            logger.info(
                f"Leave request notification sent to {', '.join(recipients)} for {employee.user.get_full_name()}"
            )
        except Exception as e:
            logger.error(f"Failed to send leave request email: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(
                f"Connection details - Host: {connection.host}, Port: {connection.port}, Username: {connection.username}"
            )
            logger.error(f"Recipients: {recipients}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")

        # Send Acknowledgment to Employee
        if employee.user.email:
            try:
                ack_subject = f"✅ Acknowledgement: {subject}"
                email = EmailMultiAlternatives(
                    ack_subject,
                    "",
                    from_email,
                    [employee.user.email],
                    connection=connection,
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                logger.info(f"Leave acknowledgment sent to {employee.user.email}")
            except Exception as e:
                logger.error(f"Failed to send leave ack to employee: {e}")

        return result

    except Exception as e:
        logger.error(f"Failed to send leave request notifications: {str(e)}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        return result


def send_regularization_request_notification(regularization_request):
    """
    Send regularization request notification to hrms@petabytz.com (MANDATORY) and reporting manager

    Args:
        regularization_request: RegularizationRequest model instance

    Returns:
        dict: Status of emails sent {'manager': bool, 'hr': bool}
    """
    result = {"manager": False, "hr": False}

    try:
        employee = regularization_request.employee
        company = employee.company

        # MANDATORY: Use hrms@petabytz.com for all regularization request notifications
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection using helper
        connection = get_hr_email_connection()

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

        # Build recipient list - MANDATORY: hrms@petabytz.com MUST receive all regularization requests
        recipients = ["hrms@petabytz.com"]

        # Add reporting manager to recipients if exists
        if employee.manager and employee.manager.email:
            recipients.append(employee.manager.email)

        # Send to all recipients (hrms@petabytz.com + manager)
        try:
            email = EmailMultiAlternatives(
                subject, "", from_email, recipients, connection=connection
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            result["hr"] = True
            if employee.manager and employee.manager.email:
                result["manager"] = True
            logger.info(
                f"Regularization request notification sent to {', '.join(recipients)} for {employee.user.get_full_name()}"
            )
        except Exception as e:
            logger.error(f"Failed to send regularization request email: {str(e)}")

        # Send Acknowledgment to Employee
        if employee.user.email:
            try:
                ack_subject = f"✅ Acknowledgement: {subject}"
                email = EmailMultiAlternatives(
                    ack_subject,
                    "",
                    from_email,
                    [employee.user.email],
                    connection=connection,
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                logger.info(
                    f"Regularization acknowledgment sent to {employee.user.email}"
                )
            except Exception as e:
                logger.error(f"Failed to send regularization ack to employee: {e}")

        return result

    except Exception as e:
        logger.error(f"Failed to send regularization request notifications: {str(e)}")
        return result


def send_welcome_email_with_link(employee, domain):
    """
    Send welcome email with activation/password reset link
    MANDATORY: Always sends from hrms@petabytz.com for all companies

    Args:
        employee: Employee model instance
        domain: Domain name for the link (e.g. 'example.com')

    Returns:
        bool: True if email sent successfully
    """
    try:
        user = employee.user
        if not user.email:
            logger.warning(f"Employee {user.get_full_name()} has no email address")
            return False

        # MANDATORY: Use hrms@petabytz.com for all welcome emails
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get standardized connection
        connection = get_hr_email_connection()

        # Generate Reset Link
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.urls import reverse

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Construct the link
        try:
            link = f"http://{domain}{reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})}"
        except:
            # Fallback if URL name differs
            link = f"http://{domain}/accounts/reset/{uid}/{token}/"

        context = {
            "employee_name": user.get_full_name(),
            "company_name": employee.company.name,
            "activation_link": link,
            "username": user.username,
        }

        try:
            html_content = render_to_string("core/emails/welcome_email.html", context)
        except:
            # Fallback Template
            html_content = f"<html><body><h2>Welcome to {employee.company.name}!</h2><p>Please activate your account: <a href='{link}'>{link}</a></p></body></html>"

        subject = f"Welcome to {employee.company.name} - Activate Your Account"
        recipient_list = [user.email]

        email = EmailMultiAlternatives(
            subject, "", from_email, recipient_list, connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(f"Welcome email sent to {user.email} from {from_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        return False


def send_leave_rejection_notification(leave_request):
    """
    Send email to employee when leave is rejected.
    MANDATORY: Uses hrms@petabytz.com as sender
    """
    try:
        employee = leave_request.employee
        company = employee.company

        # MANDATORY: Use hrms@petabytz.com for all leave notifications
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection using helper
        connection = get_hr_email_connection()

        # Determine who rejected
        rejected_by = "Management"
        if leave_request.approved_by:
            rejected_by = leave_request.approved_by.get_full_name()
            if leave_request.approved_by == employee.manager:
                rejected_by += " (Manager)"
            elif leave_request.approved_by.role == "COMPANY_ADMIN":
                rejected_by += " (HR/Admin)"

        context = {
            "employee_name": employee.user.get_full_name(),
            "leave_type": leave_request.get_leave_type_display(),
            "start_date": leave_request.start_date.strftime("%d %B %Y"),
            "end_date": leave_request.end_date.strftime("%d %B %Y"),
            "total_days": leave_request.total_days,
            "rejection_reason": leave_request.rejection_reason or "No reason provided",
            "rejected_by": rejected_by,
            "company_name": company.name,
        }

        # Render HTML email
        try:
            html_content = render_to_string(
                "core/emails/leave_rejection_notification.html", context
            )
        except Exception as e:
            logger.error(f"Failed to render leave rejection template: {e}")
            # Fallback to simple HTML
            html_content = f"""
            <html>
            <body>
                <h2>Leave Request Rejected</h2>
                <p>Dear {context["employee_name"]},</p>
                <p>Your leave request has been REJECTED.</p>
                <p><strong>Reason:</strong> {context["rejection_reason"]}</p>
                <p><strong>Rejected By:</strong> {context["rejected_by"]}</p>
            </body>
            </html>
            """

        subject = f"❌ Leave Request Rejected: {leave_request.get_leave_type_display()}"

        email = EmailMultiAlternatives(
            subject, "", from_email, [employee.user.email], connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(f"Leave rejection email sent to {employee.user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send leave rejection email: {str(e)}")
        return False


def send_regularization_rejection_notification(reg_request):
    """
    Send email when regularization is rejected.
    MANDATORY: Uses hrms@petabytz.com as sender
    """
    try:
        employee = reg_request.employee
        company = employee.company

        # MANDATORY: Use hrms@petabytz.com for all regularization notifications
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection using helper
        connection = get_hr_email_connection()

        context = {
            "employee_name": employee.user.get_full_name(),
            "date": reg_request.date.strftime("%d %B %Y"),
            "reason": reg_request.manager_comment or "No reason provided",
            "company_name": company.name,
        }

        html_content = f"""
        <html>
        <body style="font-family: sans-serif; color: #333;">
            <h2 style="color: #d32f2f;">Regularization Request Rejected</h2>
            <p>Dear {context["employee_name"]},</p>
            <p>Your Attendance Regularization for <strong>{context["date"]}</strong> has been <strong>rejected</strong>.</p>
            <p><strong>Reason:</strong> {context["reason"]}</p>
            <br>
            <p style="color: #666;">Regards,<br>{context["company_name"]} Team</p>
        </body>
        </html>
        """

        subject = f"❌ Regularization Rejected: {context['date']}"

        email = EmailMultiAlternatives(
            subject, "", from_email, [employee.user.email], connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        logger.info(f"Regularization rejection email sent to {employee.user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send regularization rejection email: {str(e)}")
        return False


def send_leave_approval_notification(leave_request):
    """
    Send email to employee when leave is APPROVED.
    MANDATORY: Uses hrms@petabytz.com as sender
    """
    try:
        employee = leave_request.employee
        company = employee.company

        # MANDATORY: Use hrms@petabytz.com for all leave notifications
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection using helper
        connection = get_hr_email_connection()

        context = {
            "employee_name": employee.user.get_full_name(),
            "leave_type": leave_request.get_leave_type_display(),
            "start_date": leave_request.start_date.strftime("%d %B %Y"),
            "end_date": leave_request.end_date.strftime("%d %B %Y"),
            "total_days": leave_request.total_days,
            "approved_by": leave_request.approved_by.get_full_name()
            if leave_request.approved_by
            else "Manager",
            "company_name": company.name,
        }

        # Render HTML email
        try:
            html_content = render_to_string(
                "core/emails/leave_approval_notification.html", context
            )
        except Exception as e:
            logger.error(f"Failed to render leave approval template: {e}")
            # Fallback to simple HTML if template fails
            html_content = f"""
            <html>
            <body>
                <h2>Leave Request Approved</h2>
                <p>Dear {context["employee_name"]},</p>
                <p>Your leave request has been APPROVED.</p>
                <p><strong>Approved By:</strong> {context["approved_by"]}</p>
            </body>
            </html>
            """

        subject = f"✅ Leave Request Approved: {context['leave_type']}"

        email = EmailMultiAlternatives(
            subject, "", from_email, [employee.user.email], connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        return True
    except Exception as e:
        logger.error(f"Failed to send leave approval email: {str(e)}")
        return False


def send_regularization_approval_notification(reg_request):
    """
    Send email when regularization is APPROVED.
    MANDATORY: Uses hrms@petabytz.com as sender
    """
    try:
        employee = reg_request.employee
        company = employee.company

        # MANDATORY: Use hrms@petabytz.com for all regularization notifications
        from_email = "Petabytz HR <hrms@petabytz.com>"

        # Get connection using helper
        connection = get_hr_email_connection()

        context = {
            "employee_name": employee.user.get_full_name(),
            "date": reg_request.date.strftime("%d %B %Y"),
            "company_name": company.name,
        }

        html_content = f"""
        <html>
        <body style="font-family: sans-serif; color: #333;">
            <h2 style="color: #2e7d32;">Regularization Request Approved</h2>
            <p>Dear {context["employee_name"]},</p>
            <p>Your Attendance Regularization request for <strong>{context["date"]}</strong> has been <strong>APPROVED</strong>.</p>
            <p>Your attendance records have been updated to 'Present' or 'On Duty' as requested.</p>
            <br>
            <p style="color: #666;">Regards,<br>{context["company_name"]} Team</p>
        </body>
        </html>
        """

        subject = f"✅ Regularization Approved: {context['date']}"

        email = EmailMultiAlternatives(
            subject, "", from_email, [employee.user.email], connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        return True
    except Exception as e:
        logger.error(f"Reg approval mail failed: {e}")
        return False
