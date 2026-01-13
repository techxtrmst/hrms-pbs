from django.contrib import admin
from .models import Employee, EmergencyContact, Attendance, AttendanceSession


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 1
    fields = ("name", "phone_number", "relationship", "is_primary")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "company",
        "department",
        "designation",
        "manager",
        "badge_id",
    )
    list_filter = (
        "company",
        "department",
        "designation",
        "employment_status",
        "is_active",
    )
    search_fields = ("user__email", "user__first_name", "user__last_name", "badge_id")
    inlines = [EmergencyContactInline]


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ("employee", "name", "phone_number", "relationship", "is_primary")
    list_filter = ("is_primary", "relationship")
    search_fields = (
        "employee__user__first_name",
        "employee__user__last_name",
        "name",
        "phone_number",
    )


from .models import HandbookSection, PolicySection


@admin.register(HandbookSection)
class HandbookSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active", "updated_at")
    list_editable = ("order", "is_active")


@admin.register(PolicySection)
class PolicySectionAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active", "updated_at")
    list_editable = ("order", "is_active")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "date", "status", "clock_in", "clock_out", 
        "daily_sessions_count", "total_working_hours", "is_currently_clocked_in"
    )
    list_filter = ("status", "date", "is_currently_clocked_in", "is_late")
    search_fields = ("employee__user__first_name", "employee__user__last_name")
    readonly_fields = ("total_working_hours",)
    date_hierarchy = "date"


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "date", "session_number", "session_type", 
        "clock_in", "clock_out", "duration_hours"
    )
    list_filter = ("session_type", "date")
    search_fields = ("employee__user__first_name", "employee__user__last_name")
    date_hierarchy = "date"
