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
        "assigned_shift_display",
    )
    list_filter = (
        "company",
        "department",
        "designation",
        "employment_status",
        "is_active",
        "assigned_shift",
    )
    search_fields = ("user__email", "user__first_name", "user__last_name", "badge_id")
    inlines = [EmergencyContactInline]

    def assigned_shift_display(self, obj):
        """Display assigned shift information"""
        if obj.assigned_shift:
            return f"{obj.assigned_shift.name} ({obj.assigned_shift.start_time.strftime('%H:%M')} - {obj.assigned_shift.end_time.strftime('%H:%M')})"
        return "No Shift Assigned"
    
    assigned_shift_display.short_description = "Assigned Shift"
    
    fieldsets = (
        ("User Information", {
            "fields": ("user", "company", "badge_id")
        }),
        ("Job Details", {
            "fields": ("department", "designation", "manager", "assigned_shift", "work_type", "date_of_joining", "location")
        }),
        ("Personal Information", {
            "fields": ("mobile_number", "personal_email", "gender", "marital_status", "dob", "profile_picture"),
            "classes": ("collapse",)
        }),
        ("Address", {
            "fields": ("permanent_address", "current_address"),
            "classes": ("collapse",)
        }),
        ("Financial Details", {
            "fields": ("bank_name", "account_number", "ifsc_code", "uan", "pan_number", "pf_enabled", "annual_ctc"),
            "classes": ("collapse",)
        }),
        ("System Fields", {
            "fields": ("employment_status", "is_active", "profile_edited"),
            "classes": ("collapse",)
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter assigned_shift choices based on company"""
        if db_field.name == "assigned_shift":
            if hasattr(request, '_obj_'):
                # Editing existing employee
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    company=request._obj_.company, is_active=True
                )
            elif request.user.company:
                # Creating new employee
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    company=request.user.company, is_active=True
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_form(self, request, obj=None, **kwargs):
        """Store object in request for formfield_for_foreignkey"""
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)


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
class AttendanceSessionAdmin(admin.ModelAdmin):
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
