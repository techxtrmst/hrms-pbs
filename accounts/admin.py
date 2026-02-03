from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from hijack.contrib.admin import HijackUserAdminMixin
from unfold.admin import ModelAdmin

from core.middleware import is_debug_mode_enabled

from .models import User


class ConditionalHijackMixin(HijackUserAdminMixin):
    """
    Hijack mixin that only enables impersonation in debug mode.

    When debug mode is disabled:
    - Hijack button is hidden from user list
    - Hijack column is not shown
    """

    def get_changelist_instance(self, request):
        """Only add hijack column when debug mode is enabled."""
        if not is_debug_mode_enabled(request):
            # Skip HijackUserAdminMixin's customization, go to parent
            return super(HijackUserAdminMixin, self).get_changelist_instance(request)
        return super().get_changelist_instance(request)


@admin.register(User)
class CustomUserAdmin(ConditionalHijackMixin, ModelAdmin, UserAdmin):
    """
    Custom User Admin with Unfold styling and hijack (impersonation).
    Hijack is only available when debug mode is enabled.
    """

    list_display = ("email", "username", "role", "company", "is_staff", "is_active")
    list_filter = ("role", "company", "is_staff", "is_active")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = UserAdmin.fieldsets + (("Company Info", {"fields": ("company", "role")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Company Info", {"fields": ("company", "role")}),)
