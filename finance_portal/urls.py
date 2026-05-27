from django.urls import path

from . import views

app_name = "finance_portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("process-bulk/", views.process_bulk_payroll, name="process_bulk_payroll"),
    path("upload-bulk-excel/", views.process_bulk_excel_upload, name="process_bulk_excel_upload"),
    path("send-email/<int:payslip_id>/", views.send_single_payslip_email_view, name="send_single_payslip_email"),
]
