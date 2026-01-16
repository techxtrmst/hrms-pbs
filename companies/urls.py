from django.urls import path
from .shift_views import shift_list, shift_create, shift_edit, shift_delete
from . import views

urlpatterns = [
    path("shifts/", shift_list, name="shift_list"),
    path("shifts/create/", shift_create, name="shift_create"),
    path("shifts/<int:pk>/edit/", shift_edit, name="shift_edit"),
    path("shifts/<int:pk>/delete/", shift_delete, name="shift_delete"),
    path("week-off-config/", views.week_off_config, name="week_off_config"),
    path("role-configuration/", views.role_configuration, name="role_configuration"),
    path(
        "announcement-configuration/",
        views.announcement_configuration,
        name="announcement_configuration",
    ),
    path(
        "api/quick-add-department/",
        views.quick_add_department,
        name="quick_add_department",
    ),
    path(
        "api/quick-add-designation/",
        views.quick_add_designation,
        name="quick_add_designation",
    ),
    path("api/quick-add-shift/", views.quick_add_shift, name="quick_add_shift"),
]
