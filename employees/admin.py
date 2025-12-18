from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'department', 'designation', 'manager')
    list_filter = ('company', 'department', 'designation')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')

from .models import HandbookSection, PolicySection

@admin.register(HandbookSection)
class HandbookSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'updated_at')
    list_editable = ('order', 'is_active')

@admin.register(PolicySection)
class PolicySectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'updated_at')
    list_editable = ('order', 'is_active')
