from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from hijack.contrib.admin import HijackUserAdminMixin
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm

from .models import User


@admin.register(User)
class CustomUserAdmin(HijackUserAdminMixin, UserAdmin, ModelAdmin, ImportExportModelAdmin):
    """
    Custom User Admin with Unfold styling, import/export, and hijack (impersonation).
    """

    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = ("email", "username", "role", "company", "is_staff", "is_active")
    list_filter = ("role", "company", "is_staff", "is_active")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = UserAdmin.fieldsets + (("Company Info", {"fields": ("company", "role")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Company Info", {"fields": ("company", "role")}),)
