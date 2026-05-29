from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.import_export.forms import ExportForm, ImportForm

from .models import (
    Attendance,
    AttendanceSession,
    EmergencyContact,
    Employee,
    HandbookSection,
    PolicySection,
)


class EmergencyContactInline(TabularInline):
    model = EmergencyContact
    extra = 1
    fields = ("name", "phone_number", "relationship", "is_primary")


@admin.register(Employee)
class EmployeeAdmin(ModelAdmin, ImportExportModelAdmin):
    """Employee admin with Unfold styling and import/export support."""

    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = (
        "user",
        "company",
        "department",
        "designation",
        "manager",
        "badge_id",
        "is_support_agent",
    )
    list_editable = ("is_support_agent",)
    list_filter = (
        "company",
        "department",
        "designation",
        "employment_status",
        "is_active",
        "is_support_agent",
    )
    search_fields = ("user__email", "user__first_name", "user__last_name", "badge_id")
    inlines = [EmergencyContactInline]


@admin.register(EmergencyContact)
class EmergencyContactAdmin(ModelAdmin):
    """Emergency Contact admin with Unfold styling."""

    list_display = ("employee", "name", "phone_number", "relationship", "is_primary")
    list_filter = ("is_primary", "relationship")
    search_fields = (
        "employee__user__first_name",
        "employee__user__last_name",
        "name",
        "phone_number",
    )


@admin.register(HandbookSection)
class HandbookSectionAdmin(ModelAdmin):
    """Handbook Section admin with Unfold styling."""

    list_display = ("title", "order", "is_active", "updated_at")
    list_editable = ("order", "is_active")


@admin.register(PolicySection)
class PolicySectionAdmin(ModelAdmin):
    """Policy Section admin with Unfold styling."""

    list_display = ("title", "order", "is_active", "updated_at")
    list_editable = ("order", "is_active")


@admin.register(Attendance)
class AttendanceAdmin(ModelAdmin, ImportExportModelAdmin):
    """Attendance admin with Unfold styling and import/export support."""

    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = (
        "employee",
        "date",
        "status",
        "clock_in",
        "clock_out",
        "daily_sessions_count",
        "total_working_hours",
        "is_currently_clocked_in",
    )
    list_filter = ("status", "date", "is_currently_clocked_in", "is_late")
    search_fields = ("employee__user__first_name", "employee__user__last_name")
    readonly_fields = ("total_working_hours",)
    date_hierarchy = "date"


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(ModelAdmin):
    """Attendance Session admin with Unfold styling."""

    list_display = (
        "employee",
        "date",
        "session_number",
        "session_type",
        "clock_in",
        "clock_out",
        "duration_hours",
    )
    list_filter = ("session_type", "date")
    search_fields = ("employee__user__first_name", "employee__user__last_name")
    date_hierarchy = "date"
