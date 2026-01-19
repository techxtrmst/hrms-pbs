from django.urls import path
from . import views

app_name = "policies"

urlpatterns = [
    # Employee Views
    path("", views.policy_list, name="policy_list"),
    path("<int:policy_id>/", views.policy_detail, name="policy_detail"),
    path(
        "<int:policy_id>/acknowledge/",
        views.acknowledge_policy,
        name="acknowledge_policy",
    ),
    # Admin Views
    path("admin/", views.admin_policy_list, name="admin_policy_list"),
    path("admin/create/", views.admin_policy_create, name="admin_policy_create"),
    path(
        "admin/<int:policy_id>/edit/", views.admin_policy_edit, name="admin_policy_edit"
    ),
    path(
        "admin/<int:policy_id>/report/",
        views.admin_acknowledgment_report,
        name="admin_acknowledgment_report",
    ),
]
