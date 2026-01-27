from django.urls import path

from companies import shift_views

# Force reload
from . import views
from .attendance_reports import attendance_late_early_report

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Me
    path("me/profile/", views.my_profile, name="my_profile"),
    path("me/home/", views.personal_home, name="personal_home"),
    path("me/leaves/", views.my_leaves, name="my_leaves"),
    path(
        "me/leaves/cancel/<int:pk>/",
        views.cancel_leave_request,
        name="cancel_my_leave_request",
    ),
    path("me/finance/", views.my_finance, name="my_finance"),
    path("me/holidays/", views.employee_holidays, name="employee_holidays"),
    path("me/handbook/", views.handbook, name="handbook"),
    path("me/policy/", views.policy, name="policy"),
    # Employees (Admin)
    path("api/search-employees/", views.search_employees_api, name="search_employees_api"),
    path("org-chart/", views.org_chart, name="org_chart"),
    path("employee/org-chart/", views.employee_org_chart, name="employee_org_chart"),
    path("analytics/attendance/", views.attendance_analytics, name="attendance_analytics"),
    path("analytics/report/", views.attendance_report, name="attendance_report"),
    path("analytics/download/", views.download_attendance, name="download_attendance"),
    path(
        "analytics/late-early/",
        attendance_late_early_report,
        name="attendance_late_early_report",
    ),
    # Leaves (Admin)
    path("leaves/requests/", views.leave_requests, name="leave_requests"),
    path("leaves/history/", views.leave_history, name="leave_history"),
    # Payroll
    path("payroll/", views.payroll_dashboard, name="payroll_dashboard"),
    path("payroll/upload/", views.upload_payslip, name="upload_payslip"),
    path("payroll/calculate/", views.calculate_generated_payslip, name="calculate_payslip"),
    path("payroll/generate/", views.process_payslip_generation, name="process_payslip_generation"),
    path("payroll/bulk-upload/", views.bulk_upload_payslips, name="bulk_payroll_upload"),
    path("payroll/download-template/", views.download_payslip_template, name="bulk_payroll_template"),



    # Config
    path("config/holidays/", views.holidays, name="holidays"),
    path(
        "config/holidays/template/",
        views.download_holiday_template,
        name="download_holiday_template",
    ),
    path("config/holidays/export/", views.export_holidays, name="export_holidays"),
    path("config/leaves/", views.company_leaves, name="company_leaves"),
    # Shift Settings
    path("config/shifts/", shift_views.shift_list, name="shift_list"),
    path("config/shifts/add/", shift_views.shift_create, name="shift_create"),
    path("config/shifts/<int:pk>/edit/", shift_views.shift_edit, name="shift_edit"),
    path("config/shifts/<int:pk>/delete/", shift_views.shift_delete, name="shift_delete"),
    # Forgot Password
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("reset-password/", views.reset_password_view, name="reset_password"),
    # Notifications
    path("api/notifications/", views.get_notifications, name="get_notifications"),
    path("api/notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("api/notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
]
