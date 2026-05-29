from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from companies.models import Company, Location
from employees.models import Employee, Payslip
from finance_portal.models import FinanceAuditLog, PayrollBatch


class FinancePortalTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create a test company
        self.company = Company.objects.create(name="Test Corp", slug="test-corp", is_active=True)

        # Create a test location
        self.location = Location.objects.create(
            name="HQ Office", company=self.company, country_code="IN", currency="INR"
        )

        # Create users
        self.finance_user = User.objects.create_user(
            email="finance@test.com",
            username="finance",
            password="password123",
            role=User.Role.EMPLOYEE,
            is_finance_manager=True,
            company=self.company,
            must_change_password=False,
        )

        self.employee_user = User.objects.create_user(
            email="emp@test.com",
            username="employee",
            password="password123",
            role=User.Role.EMPLOYEE,
            is_finance_manager=False,
            company=self.company,
            must_change_password=False,
        )

        # Create employee profile
        self.employee = Employee.objects.create(
            user=self.employee_user,
            company=self.company,
            location=self.location,
            badge_id="EMP001",
            annual_ctc=600000.0,
            date_of_joining=date(2025, 1, 1),
            pf_enabled=True,
            is_active=True,
            employment_status="ACTIVE",
        )

        # URL targets
        self.dashboard_url = reverse("finance_portal:dashboard")
        self.bulk_url = reverse("finance_portal:process_bulk_payroll")

    def test_access_control_unauthenticated(self):
        """Unauthenticated requests are redirected to login"""
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, "/accounts/login/")

    def test_access_control_denied_for_standard_employee(self):
        """Standard employees are denied access with an error message"""
        self.client.login(username="emp@test.com", password="password123")
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, "/")

        # Check that standard employee cannot trigger bulk payroll
        response = self.client.post(self.bulk_url, {"company_id": "all", "month": 5, "year": 2026})
        self.assertRedirects(response, "/")

    def test_access_granted_for_finance_manager(self):
        """Finance managers are granted access to dashboard and roster list"""
        self.client.login(username="finance@test.com", password="password123")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centralized Payroll Portal")
        self.assertContains(response, "Test Corp")
        self.assertContains(response, "EMP001")

    def test_bulk_payroll_processing(self):
        """Bulk payroll generates payslips, registers batches, and log audits"""
        self.client.login(username="finance@test.com", password="password123")

        # Roster starts with no payslips
        self.assertEqual(Payslip.objects.count(), 0)
        self.assertEqual(PayrollBatch.objects.count(), 0)
        self.assertEqual(FinanceAuditLog.objects.count(), 0)

        # Trigger processing for May 2026
        response = self.client.post(
            self.bulk_url,
            {
                "company_id": self.company.id,
                "month": 5,
                "year": 2026,
                "auto_send_email": "off",  # Turn off email sending in tests to prevent connection attempts
            },
        )

        self.assertRedirects(response, f"/finance/?company={self.company.id}&month=5&year=2026")

        # Verify Payslip creation & breakdown calculations
        self.assertEqual(Payslip.objects.count(), 1)
        payslip = Payslip.objects.first()
        self.assertEqual(payslip.employee, self.employee)
        self.assertEqual(payslip.month, date(2026, 5, 1))

        # 600,000 CTC annual -> 50,000 gross/CTC monthly
        self.assertTrue(payslip.gross_salary > 0)
        self.assertTrue(payslip.net_salary > 0)

        # Verify Batch execution record
        self.assertEqual(PayrollBatch.objects.count(), 1)
        batch = PayrollBatch.objects.first()
        self.assertEqual(batch.month, 5)
        self.assertEqual(batch.year, 2026)
        self.assertEqual(batch.status, "COMPLETED")
        self.assertEqual(batch.total_employees, 1)
        self.assertEqual(batch.processed_employees, 1)
        self.assertTrue(batch.total_amount > 0)

        # Verify Audit Log
        self.assertEqual(FinanceAuditLog.objects.count(), 1)
        log = FinanceAuditLog.objects.first()
        self.assertEqual(log.user, self.finance_user)
        self.assertEqual(log.action, "BULK_PAYROLL_PROCESS")
        self.assertEqual(log.company, self.company)
        self.assertIn("Processed bulk payroll", log.details)

    def test_bulk_excel_upload_processing(self):
        """Uploading a populated Excel sheet calculates salaries, compiles PDFs, and logs batches"""
        self.client.login(username="finance@test.com", password="password123")

        # Create an in-memory Excel workbook
        import io

        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active

        # Row 1: Header / Title (which views.py handles safely)
        ws.append(["Bulk Payslip Upload Template"])
        # Row 2: Columns Headers
        ws.append(["Employee Number", "Monthly Earned Gross", "No of Payable Units (days / hours / units)"])
        # Row 3: Employee Data
        ws.append(["EMP001", 50000.0, 31.0])

        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        excel_file.name = "bulk_payroll.xlsx"

        # Roster starts with no payslips
        self.assertEqual(Payslip.objects.count(), 0)
        self.assertEqual(PayrollBatch.objects.count(), 0)
        self.assertEqual(FinanceAuditLog.objects.count(), 0)

        # POST to Excel uploader route
        upload_url = reverse("finance_portal:process_bulk_excel_upload")
        response = self.client.post(
            upload_url,
            {
                "company_id": self.company.id,
                "month": 5,
                "year": 2026,
                "excel_file": excel_file,
                "auto_send_email": "off",
            },
        )

        self.assertRedirects(response, f"/finance/?company={self.company.id}&month=5&year=2026")

        # Verify Payslip creation & breakdown calculations
        self.assertEqual(Payslip.objects.count(), 1)
        payslip = Payslip.objects.first()
        self.assertEqual(payslip.employee, self.employee)
        self.assertEqual(payslip.month, date(2026, 5, 1))
        self.assertEqual(payslip.worked_days, 31.0)
        self.assertTrue(payslip.gross_salary > 0)

        # Verify Batch execution record
        self.assertEqual(PayrollBatch.objects.count(), 1)
        batch = PayrollBatch.objects.first()
        self.assertEqual(batch.status, "COMPLETED")
        self.assertEqual(batch.total_employees, 1)
        self.assertEqual(batch.processed_employees, 1)
        self.assertTrue(batch.total_amount > 0)

        # Verify Audit Log
        self.assertEqual(FinanceAuditLog.objects.count(), 1)
        log = FinanceAuditLog.objects.first()
        self.assertEqual(log.user, self.finance_user)
        self.assertEqual(log.action, "EXCEL_BULK_PAYROLL")
