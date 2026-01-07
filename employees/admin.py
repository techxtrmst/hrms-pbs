from django.contrib import admin
from .models import Employee, EmergencyContact


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
