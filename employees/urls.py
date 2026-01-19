from django.urls import path
from . import views
from .multi_step_views import add_employee_step1, add_employee_step2, add_employee_step3

urlpatterns = [
    path("", views.EmployeeListView.as_view(), name="employee_list"),
    path("add/", views.EmployeeCreateView.as_view(), name="employee_add"),
    path(
        "import/", views.BulkEmployeeImportView.as_view(), name="employee_bulk_import"
    ),
    path(
        "import/download-sample/",
        views.download_sample_import_file,
        name="download_sample_import_file",
    ),
    # Multi-step employee creation
    path("add/step1/", add_employee_step1, name="add_employee_step1"),
    path("add/step2/", add_employee_step2, name="add_employee_step2"),
    path("add/step3/", add_employee_step3, name="add_employee_step3"),
    path("<int:pk>/detail/", views.employee_detail, name="employee_detail"),
    path("<int:pk>/edit/", views.EmployeeUpdateView.as_view(), name="employee_edit"),
    path(
        "<int:pk>/delete/", views.EmployeeDeleteView.as_view(), name="employee_delete"
    ),
    path(
        "<int:pk>/resend-welcome/",
        views.resend_welcome_email,
        name="resend_welcome_email",
    ),
    path("employee-profile/", views.employee_profile, name="employee_profile"),
    # Leave Management
    path("leave/apply/", views.LeaveApplyView.as_view(), name="leave_apply"),
    path("leave/<int:pk>/approve/", views.approve_leave, name="approve_leave"),
    path("leave/<int:pk>/reject/", views.reject_leave, name="reject_leave"),
    path(
        "api/leave/check-balance/",
        views.check_leave_balance,
        name="api_check_leave_balance",
    ),
    # API endpoints for attendance
    path("api/clock-in/", views.clock_in, name="api_clock_in"),
    path("api/clock-out/", views.clock_out, name="api_clock_out"),
    path("api/update-location/", views.update_location, name="api_update_location"),
    path(
        "api/attendance/<int:pk>/map-data/",
        views.get_attendance_map_data,
        name="api_attendance_map_data",
    ),
    # Location Tracking API endpoints
    path(
        "api/location/hourly/",
        views.submit_hourly_location,
        name="api_submit_hourly_location",
    ),
    path(
        "api/location/status/",
        views.get_location_tracking_status,
        name="api_location_tracking_status",
    ),
    path(
        "api/location/history/<int:employee_id>/",
        views.get_employee_location_history,
        name="api_employee_location_history",
    ),
    path("attendance/<int:pk>/map/", views.attendance_map, name="attendance_map"),
    # Employee Exit Actions
    path(
        "<int:pk>/exit-action/", views.employee_exit_action, name="employee_exit_action"
    ),
    path(
        "exit-initiatives/", views.exit_initiatives_list, name="exit_initiatives_list"
    ),
    path(
        "exit-initiatives/<int:pk>/approve/",
        views.approve_exit_initiative,
        name="approve_exit_initiative",
    ),
    path(
        "exit-initiatives/<int:pk>/reject/",
        views.reject_exit_initiative,
        name="reject_exit_initiative",
    ),
    # ID Proof Management
    path("<int:pk>/id-proofs/", views.employee_id_proofs, name="employee_id_proofs"),
    # Leave Configuration
    path("leave/configuration/", views.leave_configuration, name="leave_configuration"),
    path(
        "leave/configuration/accrue/",
        views.run_monthly_accrual,
        name="run_monthly_accrual",
    ),
    path(
        "leave/balance/<int:pk>/update/",
        views.update_leave_balance,
        name="update_leave_balance",
    ),
    # Regularization
    path(
        "regularization/apply/",
        views.RegularizationCreateView.as_view(),
        name="regularization_apply",
    ),
    path(
        "regularization/requests/",
        views.RegularizationListView.as_view(),
        name="regularization_list",
    ),
    path(
        "regularization/<int:pk>/approve/",
        views.approve_regularization,
        name="regularization_approve",
    ),
    path(
        "regularization/<int:pk>/reject/",
        views.reject_regularization,
        name="regularization_reject",
    ),
    # Emergency Contacts
    path(
        "emergency-contact/add/",
        views.add_emergency_contact,
        name="add_emergency_contact",
    ),
    path(
        "emergency-contact/<int:contact_id>/update/",
        views.update_emergency_contact,
        name="update_emergency_contact",
    ),
    path(
        "emergency-contact/<int:contact_id>/delete/",
        views.delete_emergency_contact,
        name="delete_emergency_contact",
    ),
]
