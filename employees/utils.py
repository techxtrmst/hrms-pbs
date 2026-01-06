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
    """
    try:
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Construct link
        reset_path = reverse(
            "password_reset_confirm", kwargs={"uidb64": uid, "token": token}
        )

        if request:
            activation_link = request.build_absolute_uri(reset_path)
        else:
            # Fallback for when request is not available
            domain = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
            activation_link = f"{domain}{reset_path}"

        subject = (
            f"Welcome to {user.employee_profile.company.name} - Activate Your Account"
        )
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

        # Create email object
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        return True
    except Exception as e:
        logger.error(f"Failed to send activation email to {user.email}: {str(e)}")
        return False
