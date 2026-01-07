from django.urls import path
from . import views

app_name = "superadmin"

urlpatterns = [
    # Main dashboard
    path("dashboard/", views.superadmin_dashboard, name="dashboard"),
    # Company context switching API
    path("api/switch-company/", views.switch_company_api, name="switch_company_api"),
    # Drill-down views
    path("companies/", views.company_list_view, name="companies"),
    path("employees/", views.employee_list_view, name="employees"),
    path("attendance/today/", views.attendance_today_view, name="attendance_today"),
    path("leaves/today/", views.leaves_today_view, name="leaves_today"),
    # Employee detail view
    path(
        "employee/<int:employee_id>/detail/",
        views.employee_detail_view,
        name="employee_detail",
    ),
    # Company monitor dashboard
    path(
        "company/<int:company_id>/monitor/",
        views.company_monitor_dashboard,
        name="company_monitor",
    ),
    # Export functionality
    path("export/<str:report_type>/", views.export_data_view, name="export_data"),
]
