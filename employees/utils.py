import logging
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_activation_email(user, request=None):
    """
    Sends an account activation email to the user.
    Enhanced with detailed logging and error handling.
    """
    try:
        # Log the attempt
        logger.info(f"Starting activation email process for user: {user.email}")

        # Check if user has employee profile
        if not hasattr(user, "employee_profile") or not user.employee_profile:
            logger.error(f"User {user.email} has no employee profile")
            return False

        # Generate token and UID
        try:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            logger.info(f"Token and UID generated successfully for {user.email}")
        except Exception as e:
            logger.error(f"Failed to generate token/UID for {user.email}: {str(e)}")
            return False

        # Construct activation link
        try:
            reset_path = reverse(
                "password_reset_confirm", kwargs={"uidb64": uid, "token": token}
            )

            if request:
                activation_link = request.build_absolute_uri(reset_path)
            else:
                # Fallback for when request is not available
                domain = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
                activation_link = f"{domain}{reset_path}"

            logger.info(f"Activation link generated: {activation_link}")
        except Exception as e:
            logger.error(
                f"Failed to generate activation link for {user.email}: {str(e)}"
            )
            return False

        # Prepare email content
        try:
            subject = f"Welcome to {user.employee_profile.company.name} - Activate Your Account"
            first_name = user.first_name or "Employee"
            company_name = user.employee_profile.company.name

            # Context for the template
            context = {
                "first_name": first_name,
                "activation_link": activation_link,
                "company_name": company_name,
            }

            # Render HTML content
            html_content = render_to_string(
                "accounts/emails/activation_email.html", context
            )
            # Create text fallback
            text_content = strip_tags(html_content)

            logger.info(f"Email content prepared for {user.email}")
        except Exception as e:
            logger.error(f"Failed to prepare email content for {user.email}: {str(e)}")
            return False

        # Get email connection and send
        try:
            # MANDATORY: Use hrms@petabytz.com for all activation emails
            from_email = "Petabytz HR <hrms@petabytz.com>"

            logger.info(f"Getting HR email connection for {user.email}")
            # Get standardized connection
            from core.email_utils import get_hr_email_connection

            connection = get_hr_email_connection()

            logger.info(f"Creating email object for {user.email}")
            # Create email object
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[user.email],
                connection=connection,
            )
            email.attach_alternative(html_content, "text/html")

            logger.info(f"Sending activation email to {user.email} from {from_email}")
            email.send(fail_silently=False)

            logger.info(
                f"✓ Activation email sent successfully to {user.email} for company {company_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send activation email to {user.email}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    except Exception as e:
        logger.error(
            f"Unexpected error in send_activation_email for {user.email}: {str(e)}"
        )
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
