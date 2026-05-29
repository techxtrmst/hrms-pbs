import logging
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import (
    LoginView,
    PasswordChangeView,
    PasswordResetConfirmView,
)
from django.db.models import Case, IntegerField, Value, When
from django.urls import reverse_lazy

from companies.models import Company

from .forms import LoginForm

logger = logging.getLogger(__name__)


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    form_class = LoginForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fetch active companies, prioritizing PetaBytz at the top
        active_companies = (
            Company.objects.filter(is_active=True)
            .annotate(
                priority=Case(
                    When(name__icontains="petabytz", then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by("priority", "name")
        )
        context["active_companies"] = active_companies

        # Define the path to the slides directory
        slides_dir = os.path.join(settings.BASE_DIR, "static", "accounts", "slides")

        # List to hold image filenames
        slide_images = []

        # Check if directory exists
        if os.path.exists(slides_dir):
            try:
                # Iterate over files in the directory
                for filename in os.listdir(slides_dir):
                    # Check for image extensions
                    # NOTE: Images optimized to AVIF format for 88%+ size reduction
                    # Original JPGs were 43.42 MB, now 4.93 MB in AVIF
                    if filename.lower().endswith((".avif", ".png", ".jpg", ".jpeg", ".gif", ".webp")):
                        # Add relative path for static tag usage
                        slide_images.append(f"accounts/slides/{filename}")
            except Exception as e:
                logger.warning("Error reading slides directory: %s", e)

        # If no images found, template falls back to Unsplash placeholder images
        context["slide_images"] = slide_images
        return context


class CustomPasswordChangeView(PasswordChangeView):
    template_name = "accounts/change_password.html"
    success_url = reverse_lazy("dashboard")  # Redirect to dashboard after success

    def form_valid(self, form):
        # Update the flag - Refetch to be safe from stale objects
        user = self.request.user
        user.must_change_password = False
        user.save(update_fields=["must_change_password"])

        logger.debug("Password changed for %s. Flag set to False.", user.email)

        # Ensure session auth hash is updated to prevent logout
        update_session_auth_hash(self.request, user)

        messages.success(self.request, "Your password has been successfully updated.")
        return super().form_valid(form)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("login")  # Redirect to login page instead

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Inject company for logo display
        if hasattr(self, "user") and self.user and self.user.company:
            context["company"] = self.user.company
            # Also update request.company so base_auth.html picks it up
            self.request.company = self.user.company
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        # The form's save method returns the user
        user = form.user
        user.must_change_password = False
        user.save(update_fields=["must_change_password"])

        # Add success message
        messages.success(
            self.request,
            "Password reset successful! Please log in with your new password.",
        )

        return response
