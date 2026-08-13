from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from companies.models import Company, Location
from employees.models import Employee, Payslip
from finance_portal.models import BankAccount, FinanceAuditLog, PayrollBatch, PurchaseRequest, Transaction


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
        response = self.client.get(self.dashboard_url + "?view=payroll")
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

        self.assertRedirects(response, f"/finance/?view=payroll&company={self.company.id}&month=5&year=2026")

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

        self.assertRedirects(response, f"/finance/?view=payroll&company={self.company.id}&month=5&year=2026")

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

    def test_travel_allowance_preview_and_generation(self):
        """Test travel allowance preview calculation and draft payslip generation"""
        self.client.login(username="finance@test.com", password="password123")

        # 1. Test preview calculation API with travel allowance
        preview_url = reverse("finance_portal:calculate_payslip_preview")
        response = self.client.post(
            preview_url,
            {
                "employee_id": self.employee.id,
                "annual_ctc": 600000.0,
                "worked_days": 30,
                "pf_enabled": True,
                "travel_allowance": 5000.0,
                "month": 5,
                "year": 2026,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["breakdown"]["travel_allowance"], 5000.0)

        # Base net with May proration (30/31 worked days, 600000 CTC, PF enabled): 46333
        # With 5,000 travel allowance: net should be 51333.0
        self.assertEqual(data["breakdown"]["net_salary"], 51333.0)

        # 2. Test draft generation via process_single_payroll
        single_process_url = reverse("finance_portal:process_single_payroll")
        response = self.client.post(
            single_process_url,
            {
                "employee_id": self.employee.id,
                "annual_ctc": 600000.0,
                "worked_days": 30,
                "pf_enabled": "on",
                "travel_allowance_enabled": "on",
                "travel_allowance": 5000.0,
                "month": 5,
                "year": 2026,
            },
        )
        self.assertRedirects(response, "/finance/?view=payroll&company=all&month=5&year=2026")

        # Verify payslip is generated with travel allowance saved to database
        # Base net for 600000 CTC (PF enabled, full May) = 46333; +5000 travel = 51333
        self.assertEqual(Payslip.objects.count(), 1)
        payslip = Payslip.objects.first()
        self.assertEqual(payslip.travel_allowance, 5000.0)
        self.assertEqual(payslip.net_salary, 51333.0)

    def test_tds_deduction_preview_and_generation(self):
        """Test TDS deduction preview calculation and draft payslip generation"""
        self.client.login(username="finance@test.com", password="password123")

        # 1. Test preview calculation API with TDS deduction
        preview_url = reverse("finance_portal:calculate_payslip_preview")
        response = self.client.post(
            preview_url,
            {
                "employee_id": self.employee.id,
                "annual_ctc": 600000.0,
                "worked_days": 30,
                "pf_enabled": True,
                "travel_allowance": 0.0,
                "tds_deduction": 2000.0,
                "month": 5,
                "year": 2026,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["breakdown"]["tds_deduction"], 2000.0)

        # Base Net with May proration (30/31 worked days): 46,333.0
        # With 2,000 TDS deduction, net should be 44,383.0
        self.assertEqual(data["breakdown"]["net_salary"], 44333.0)

        # 2. Test draft generation via process_single_payroll
        single_process_url = reverse("finance_portal:process_single_payroll")
        response = self.client.post(
            single_process_url,
            {
                "employee_id": self.employee.id,
                "annual_ctc": 600000.0,
                "worked_days": 30,
                "pf_enabled": "on",
                "tds_deduction_enabled": "on",
                "tds_deduction": 2000.0,
                "month": 5,
                "year": 2026,
            },
        )
        self.assertRedirects(response, "/finance/?view=payroll&company=all&month=5&year=2026")

        # Verify payslip is generated with TDS deduction saved to database
        # Base net for 600000 CTC (PF enabled, full May) = 46333; -2000 TDS = 44333
        self.assertEqual(Payslip.objects.count(), 1)
        payslip = Payslip.objects.first()
        self.assertEqual(payslip.tds_deduction, 2000.0)
        self.assertEqual(payslip.net_salary, 44333.0)

    def test_save_draft_payslip_with_travel_and_tds(self):
        """Test save_draft_payslip endpoint correctly saves and recalculates travel_allowance and tds_deduction"""
        self.client.login(username="finance@test.com", password="password123")

        # Create initial draft payslip via process_single_payroll
        single_process_url = reverse("finance_portal:process_single_payroll")
        self.client.post(
            single_process_url,
            {
                "employee_id": self.employee.id,
                "annual_ctc": 600000.0,
                "worked_days": 30,
                "pf_enabled": "on",
                "month": 5,
                "year": 2026,
            },
        )
        payslip = Payslip.objects.get(employee=self.employee, month="2026-05-01")

        # Now save draft with travel allowance and TDS deduction
        save_draft_url = reverse("finance_portal:save_draft_payslip")
        response = self.client.post(
            save_draft_url,
            {
                "payslip_id": payslip.id,
                "worked_days": 30,
                "basic": 25000.0,
                "hra": 10000.0,
                "conveyance_allowance": 1600.0,
                "special_allowance": 12783.0,
                "travel_allowance": 4000.0,
                "professional_tax": 200.0,
                "employee_pf": 1800.0,
                "employer_pf": 1800.0,
                "tds_deduction": 3000.0,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")

        # Refresh from database and assert
        payslip.refresh_from_db()
        self.assertEqual(payslip.travel_allowance, 4000.0)
        self.assertEqual(payslip.tds_deduction, 3000.0)
        # Gross should be 25000 + 10000 + 1600 + 12783 + 4000 = 53383.0
        self.assertEqual(payslip.gross_salary, 53383.0)
        # Net = 53383 - 1800 (emp_pf) - 200 (PT) - 3000 (TDS) = 48383.0
        # NOTE: test uses manually set employer_pf=1800 (from the draft payload), not auto-calculated 1950
        self.assertEqual(payslip.net_salary, 48383.0)

    def test_recalculate_components_with_travel_and_tds(self):
        """Test recalculate_components endpoint correctly preserves/updates travel_allowance and tds_deduction"""
        self.client.login(username="finance@test.com", password="password123")

        # Create initial draft payslip
        single_process_url = reverse("finance_portal:process_single_payroll")
        self.client.post(
            single_process_url,
            {
                "employee_id": self.employee.id,
                "annual_ctc": 600000.0,
                "worked_days": 30,
                "pf_enabled": "on",
                "month": 5,
                "year": 2026,
            },
        )
        payslip = Payslip.objects.get(employee=self.employee, month="2026-05-01")

        # Call recalculate endpoint with new ctc, travel allowance, and TDS
        recalc_url = reverse("finance_portal:recalculate_components")
        response = self.client.post(
            recalc_url,
            {
                "payslip_id": payslip.id,
                "annual_ctc": 720000.0,
                "worked_days": 30,
                "travel_allowance": 5000.0,
                "tds_deduction": 4000.0,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")

        # Check values returned in response
        self.assertEqual(data["travel_allowance"], 5000.0)
        self.assertEqual(data["tds_deduction"], 4000.0)

        # Refresh and verify database state
        payslip.refresh_from_db()
        self.assertEqual(payslip.travel_allowance, 5000.0)
        self.assertEqual(payslip.tds_deduction, 4000.0)
        self.assertEqual(payslip.employee.annual_ctc, 720000.0)


class TransactionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name="Test Corp", slug="test-corp", is_active=True)
        self.finance_user = User.objects.create_user(
            email="finance2@test.com",
            username="finance2",
            password="password123",
            role=User.Role.EMPLOYEE,
            is_finance_manager=True,
            company=self.company,
            must_change_password=False,
        )
        self.bank_account = BankAccount.objects.create(
            bank_name="Test Bank",
            account_number="1234567890",
            branch_name="Main Branch",
            ifsc_code="TEST0001234",
            balance=10000.00,
            status="active",
        )
        self.purchase_request = PurchaseRequest.objects.create(
            raised_by=self.finance_user,
            item_name="Office Chair",
            description="Ergonomic office chair for developer",
            reason="Old chair is broken",
            estimated_amount=1500.00,
            status="approved",
        )
        self.submit_url = reverse("finance_portal:transaction_submit")

    def test_submit_debit_transaction(self):
        self.client.login(username="finance2@test.com", password="password123")
        import io

        screenshot = io.BytesIO(b"dummy screenshot content")
        screenshot.name = "receipt.jpg"

        response = self.client.post(
            self.submit_url,
            {
                "purchase_request_id": self.purchase_request.id,
                "bank_account_id": self.bank_account.id,
                "transaction_id": "TXNDEB123",
                "amount": "1500.00",
                "transaction_type": "debit",
                "screenshot": screenshot,
            },
        )
        self.assertRedirects(response, self.submit_url)

        # Verify bank account balance was deducted
        self.bank_account.refresh_from_db()
        self.assertEqual(self.bank_account.balance, 8500.00)

        # Verify transaction was created
        tx = Transaction.objects.get(transaction_id="TXNDEB123")
        self.assertEqual(tx.transaction_type, "debit")
        self.assertEqual(tx.amount, 1500.00)
        self.assertEqual(tx.status, "completed")

        # Verify audit log
        log = FinanceAuditLog.objects.filter(action="BALANCE_DEDUCTION").first()
        self.assertIsNotNone(log)
        self.assertIn("Deducted 1500.00", log.details)

    def test_submit_credit_transaction(self):
        self.client.login(username="finance2@test.com", password="password123")
        import io

        screenshot = io.BytesIO(b"dummy screenshot content")
        screenshot.name = "deposit.jpg"

        response = self.client.post(
            self.submit_url,
            {
                "bank_account_id": self.bank_account.id,
                "transaction_id": "TXNCRD123",
                "amount": "5000.00",
                "transaction_type": "credit",
                "screenshot": screenshot,
            },
        )
        self.assertRedirects(response, self.submit_url)

        # Verify bank account balance was added
        self.bank_account.refresh_from_db()
        self.assertEqual(self.bank_account.balance, 15000.00)

        # Verify transaction was created
        tx = Transaction.objects.get(transaction_id="TXNCRD123")
        self.assertEqual(tx.transaction_type, "credit")
        self.assertEqual(tx.amount, 5000.00)
        self.assertEqual(tx.status, "completed")
        self.assertIsNone(tx.purchase_request)

        # Verify audit log
        log = FinanceAuditLog.objects.filter(action="BALANCE_ADDITION").first()
        self.assertIsNotNone(log)
        self.assertIn("Credited 5000.00", log.details)
