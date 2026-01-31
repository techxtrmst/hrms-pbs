from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm

from .models import Announcement, Company, Holiday, Location, ShiftSchedule


@admin.register(Company)
class CompanyAdmin(ModelAdmin, ImportExportModelAdmin):
    """Company admin with Unfold styling and import/export support."""

    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = (
        "name",
        "primary_domain",
        "email_domain",
        "location",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "primary_domain", "email_domain")
    list_filter = ("is_active", "location")


@admin.register(Location)
class LocationAdmin(ModelAdmin, ImportExportModelAdmin):
    """Location admin with Unfold styling and import/export support."""

    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = ("name", "company", "country_code", "currency", "timezone", "is_active")
    list_filter = ("company", "country_code", "currency", "is_active")
    search_fields = ("name", "company__name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("company", "name", "country_code", "currency", "timezone", "is_active")},
        ),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Holiday)
class HolidayAdmin(ModelAdmin, ImportExportModelAdmin):
    """Holiday admin with Unfold styling and import/export support."""

    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = ("name", "company", "date", "location", "holiday_type", "is_active")
    search_fields = ("name", "company__name")
    list_filter = ("company", "location", "holiday_type", "is_active", "year")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ShiftSchedule)
class ShiftScheduleAdmin(ModelAdmin, ImportExportModelAdmin):
    """Shift Schedule admin with Unfold styling and import/export support."""

    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = (
        "name",
        "company",
        "start_time",
        "end_time",
        "grace_period_minutes",
        "is_active",
    )
    search_fields = ("name", "company__name")
    list_filter = ("company", "is_active")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Basic Information", {"fields": ("company", "name", "is_active")}),
        (
            "Shift Timings",
            {
                "fields": (
                    "start_time",
                    "end_time",
                    "lunch_break_start",
                    "lunch_break_end",
                )
            },
        ),
        (
            "Attendance Rules",
            {"fields": ("grace_period_minutes", "early_departure_threshold_minutes")},
        ),
        (
            "Working Days",
            {
                "fields": (
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                )
            },
        ),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Announcement)
class AnnouncementAdmin(ModelAdmin):
    """Announcement admin with Unfold styling."""

    list_display = ("title", "company", "location", "is_active", "created_at")
    search_fields = ("title", "content", "company__name")
    list_filter = ("company", "location", "is_active", "created_at")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Basic Information", {"fields": ("company", "location", "title")}),
        ("Content", {"fields": ("content",)}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
