from django.contrib import admin
from .models import AttritionRisk, ResumeParsingJob


@admin.register(AttritionRisk)
class AttritionRiskAdmin(admin.ModelAdmin):
    list_display = ("employee", "risk_level", "risk_score", "last_updated")
    list_filter = ("risk_level", "last_updated")
    search_fields = (
        "employee__user__first_name",
        "employee__user__last_name",
        "employee__user__email",
    )
    readonly_fields = ("last_updated",)


@admin.register(ResumeParsingJob)
class ResumeParsingJobAdmin(admin.ModelAdmin):
    list_display = ("id", "parsed_name", "parsed_email", "status", "uploaded_at")
    list_filter = ("status", "uploaded_at")
    search_fields = ("parsed_name", "parsed_email")
