from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "username", "role", "company", "is_staff")
    list_filter = ("role", "company", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Company Info", {"fields": ("company", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Company Info", {"fields": ("company", "role")}),
    )
