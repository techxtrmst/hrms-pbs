from django.urls import path

from . import views

app_name = "finance_portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("process-bulk/", views.process_bulk_payroll, name="process_bulk_payroll"),
    path("process-draft/", views.process_draft_payroll, name="process_draft_payroll"),
    path("save-draft-payslip/", views.save_draft_payslip, name="save_draft_payslip"),
    path("update-ctc/", views.update_employee_ctc, name="update_employee_ctc"),
    path("upload-bulk-excel/", views.process_bulk_excel_upload, name="process_bulk_excel_upload"),
    path("send-email/<int:payslip_id>/", views.send_single_payslip_email_view, name="send_single_payslip_email"),
    path("preview-draft/<int:payslip_id>/", views.preview_draft_payslip, name="preview_draft_payslip"),
]
