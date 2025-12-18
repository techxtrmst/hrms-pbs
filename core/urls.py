from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # Me
    path("me/profile/", views.my_profile, name="my_profile"),
    path("me/home/", views.personal_home, name="personal_home"),
    path("me/leaves/", views.my_leaves, name="my_leaves"),
    path("me/finance/", views.my_finance, name="my_finance"),
    path("me/handbook/", views.handbook, name="handbook"),
    path("me/policy/", views.policy, name="policy"),

    # Employees (Admin)
    path("org-chart/", views.org_chart, name="org_chart"),
    path("analytics/attendance/", views.attendance_analytics, name="attendance_analytics"),
    path("analytics/report/", views.attendance_report, name="attendance_report"),
    path("analytics/download/", views.download_attendance, name="download_attendance"),

    # Leaves (Admin)
    path("leaves/requests/", views.leave_requests, name="leave_requests"),
    path("leaves/history/", views.leave_history, name="leave_history"),

    # Payroll
    path("payroll/", views.payroll_dashboard, name="payroll_dashboard"),

    # Config
    path("config/holidays/", views.holidays, name="holidays"),
    path("config/leaves/", views.company_leaves, name="company_leaves"),
]
