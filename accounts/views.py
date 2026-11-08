import logging
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    PasswordChangeView,
    PasswordResetConfirmView,
)
from django.db.models import Case, IntegerField, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from companies.models import Company

from .forms import LoginForm
from .models import LinkedAccount, User

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


@login_required
@require_POST
def link_account_api(request):
    """
    API endpoint to authenticate and link an additional account from another entity or role.
    Stores the linked account in the session for quick 1-click switching.
    """
    current_user = request.user
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    switch_now = request.POST.get("switch_now", "false").lower() in ["true", "1", "yes"]

    if not email or not password:
        return JsonResponse({"success": False, "message": "Email and password are required."}, status=400)

    # Attempt authentication with email/username
    user = authenticate(request, username=email, password=password)
    if not user:
        try:
            user_obj = User.objects.get(email__iexact=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            user = None

    if user is None:
        return JsonResponse({"success": False, "message": "Invalid email or password."}, status=400)

    if not user.is_active:
        return JsonResponse(
            {"success": False, "message": "This account is inactive. Please contact your administrator."}, status=400
        )

    # Save permanent bidirectional links in the database
    LinkedAccount.objects.get_or_create(primary_user=current_user, linked_user=user)
    LinkedAccount.objects.get_or_create(primary_user=user, linked_user=current_user)

    # Link all accounts in the group
    c_ids = set(LinkedAccount.objects.filter(primary_user=current_user).values_list("linked_user_id", flat=True))
    t_ids = set(LinkedAccount.objects.filter(primary_user=user).values_list("linked_user_id", flat=True))
    cluster_ids = c_ids | t_ids | {current_user.id, user.id}

    cluster_users = list(User.objects.filter(id__in=cluster_ids, is_active=True))
    for u1 in cluster_users:
        for u2 in cluster_users:
            if u1.id != u2.id:
                LinkedAccount.objects.get_or_create(primary_user=u1, linked_user=u2)

    # Ensure current user is in linked accounts
    session_accounts = list(request.session.get("linked_accounts", []))

    # Helper to format account entry
    def format_acc_dict(u, is_curr=False):
        u_avatar = ""
        u_desig = ""
        if hasattr(u, "employee_profile") and u.employee_profile:
            u_desig = u.employee_profile.designation or ""
            if u.employee_profile.profile_picture:
                try:
                    u_avatar = u.employee_profile.profile_picture.url
                except Exception:
                    u_avatar = ""
        return {
            "user_id": u.id,
            "email": u.email,
            "full_name": u.get_full_name() or u.username,
            "company_name": u.company.name if u.company else "HRMS Portal",
            "company_slug": u.company.slug if u.company else "",
            "role": u.role,
            "role_display": u.get_role_display() if hasattr(u, "get_role_display") else u.role,
            "designation": u_desig,
            "avatar_url": u_avatar,
            "is_current": is_curr,
        }

    # Add current user if missing
    if not any(acc.get("user_id") == current_user.id for acc in session_accounts):
        session_accounts.append(format_acc_dict(current_user, is_curr=True))

    # Add newly linked user if not already present
    if not any(acc.get("user_id") == user.id for acc in session_accounts):
        session_accounts.append(format_acc_dict(user, is_curr=(user.id == current_user.id)))

    request.session["linked_accounts"] = session_accounts
    request.session.modified = True

    if switch_now and user.id != current_user.id:
        # Switch immediately
        auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        # Ensure session accounts persist across session rotation
        request.session["linked_accounts"] = session_accounts
        request.session.modified = True
        messages.success(
            request,
            f"Switched to {user.get_full_name() or user.email} ({user.company.name if user.company else 'HRMS'})",
        )
        return JsonResponse(
            {
                "success": True,
                "message": "Account linked and switched successfully.",
                "redirect_url": reverse("dashboard"),
            }
        )

    company_name = user.company.name if user.company else "HRMS Portal"
    return JsonResponse(
        {
            "success": True,
            "message": f"Account for {user.get_full_name() or user.email} ({company_name}) linked successfully!",
            "account": format_acc_dict(user, is_curr=False),
        }
    )


@login_required
@require_POST
def switch_account_view(request, user_id):
    """
    One-click switcher to switch active session to another linked account.
    """
    target_user = get_object_or_404(User, id=user_id, is_active=True)

    # Check if target_user is linked in DB or current user is admin/superuser
    is_linked = LinkedAccount.objects.filter(primary_user=request.user, linked_user=target_user).exists()
    is_admin = request.user.is_superuser or request.user.role in [User.Role.SUPERADMIN, User.Role.COMPANY_ADMIN]

    if not is_linked and not is_admin:
        messages.error(request, "You do not have permission to switch to this account. Please link it first.")
        return redirect("dashboard")

    # If is_admin and not linked yet in DB, establish mutual link
    if not is_linked:
        LinkedAccount.objects.get_or_create(primary_user=request.user, linked_user=target_user)
        LinkedAccount.objects.get_or_create(primary_user=target_user, linked_user=request.user)

    current_company_id = request.user.company_id

    # Switch session
    auth_login(request, target_user, backend="django.contrib.auth.backends.ModelBackend")

    company_name = target_user.company.name if target_user.company else "HRMS Portal"
    messages.success(request, f"Switched to {target_user.get_full_name() or target_user.email} ({company_name})")

    # If switching across different companies, redirect to dashboard to prevent company-specific 404s
    next_url = request.POST.get("next") or request.GET.get("next") or reverse("dashboard")
    if current_company_id != target_user.company_id:
        next_url = reverse("dashboard")

    return redirect(next_url)


@login_required
@require_POST
def remove_linked_account_api(request, user_id):
    """
    Remove an account from the linked accounts switcher permanently from DB and current session.
    """
    if user_id == request.user.id:
        return JsonResponse(
            {"success": False, "message": "Cannot remove currently active account from switcher."}, status=400
        )

    LinkedAccount.objects.filter(primary_user=request.user, linked_user_id=user_id).delete()
    LinkedAccount.objects.filter(primary_user_id=user_id, linked_user=request.user).delete()

    session_accounts = request.session.get("linked_accounts", [])
    updated_accounts = [acc for acc in session_accounts if acc.get("user_id") != user_id]
    request.session["linked_accounts"] = updated_accounts
    request.session.modified = True

    return JsonResponse({"success": True, "message": "Account removed from switcher."})
