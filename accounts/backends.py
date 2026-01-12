from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
import logging

logger = logging.getLogger(__name__)


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"

    def form_valid(self, form):
        # Already authenticated by AuthenticationForm, but check redirection logic
        user = form.get_user()

        # Check if password change is required (Logic could be: last_login is None, or a specific flag)
        # For now, we will just rely on the user manually changing pass,
        # or we can force it if user.last_login is None

        login(self.request, user)
        return redirect(self.get_success_url())


class CustomAuthenticationBackend:
    """
    Allow login via Email OR Badge ID
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        from django.contrib.auth import get_user_model
        from employees.models import Employee

        User = get_user_model()

        try:
            # 1. Try fetching by Email (Username in our model matches email)
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            try:
                # 2. Try fetching by Badge ID
                employee = Employee.objects.get(badge_id=username)
                user = employee.user
            except Employee.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        is_active = getattr(user, "is_active", None)
        return is_active or is_active is None

    def get_user(self, user_id):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
