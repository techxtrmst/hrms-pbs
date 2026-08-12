from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from companies.models import Company, Location
from core.models import Notification
from employees.models import Attendance, Employee, RegularizationRequest

User = get_user_model()


class AutomatedWeekOffRequestTestCase(TestCase):
    def setUp(self):
        # Create company
        self.company = Company.objects.create(name="Test Company", hr_email="hr@test.com")

        # Create location
        self.location = Location.objects.create(company=self.company, name="Main Office", timezone="Asia/Kolkata")

        # Create manager
        self.manager_user = User.objects.create_user(
            username="manager",
            email="manager@test.com",
            password="password",
            role=User.Role.MANAGER,
            company=self.company,
            must_change_password=False,
        )
        self.manager_employee = Employee.objects.create(
            user=self.manager_user, company=self.company, designation="Manager", department="HR", badge_id="MGR001"
        )

        # Create employee with a scheduled week-off
        self.employee_user = User.objects.create_user(
            username="employee",
            email="employee@test.com",
            password="password",
            role=User.Role.EMPLOYEE,
            company=self.company,
            must_change_password=False,
        )
        self.employee = Employee.objects.create(
            user=self.employee_user,
            company=self.company,
            manager=self.manager_user,  # Using manager_user
            designation="Developer",
            department="Engineering",
            badge_id="EMP001",
            week_off_monday=True,  # Set Monday as week-off
            week_off_tuesday=False,
            week_off_wednesday=False,
            week_off_thursday=False,
            week_off_friday=False,
            week_off_saturday=False,
            week_off_sunday=False,
        )

        # Assign location to employee profile
        self.employee.assigned_location = self.location
        self.employee.save()

        self.client = Client()
        self.client.login(username="employee@test.com", password="password")

    def test_clock_in_on_week_off(self):
        # We need to clock in on a Monday to trigger week-off detection
        # Monday is 2026-06-08
        monday_date = date(2026, 6, 8)

        # We will patch timezone.now to return a datetime on 2026-06-08
        from unittest.mock import patch

        import pytz

        tz = pytz.timezone("Asia/Kolkata")
        mock_now = tz.localize(timezone.datetime(2026, 6, 8, 10, 0, 0))

        with patch("django.utils.timezone.now", return_value=mock_now):
            # Attempt clock-in
            response = self.client.post(
                "/employees/api/clock-in/",
                {
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                    "accuracy": 10,
                    "clock_in_type": "OFFICE",
                    "timezone": "Asia/Kolkata",
                },
                content_type="application/json",
            )

            self.assertEqual(response.status_code, 200)

            # Check if Attendance record was created for that date
            attendance = Attendance.objects.filter(employee=self.employee, date=monday_date).first()
            self.assertIsNotNone(attendance)
            self.assertTrue(attendance.is_currently_clocked_in)

            # Assert that NO RegularizationRequest with change_type WEEK_OFF_WORK was created
            reg_req_exists = RegularizationRequest.objects.filter(
                employee=self.employee, date=monday_date, change_type="WEEK_OFF_WORK"
            ).exists()
            self.assertFalse(reg_req_exists)

            # Assert that NO Notification was created for manager
            notification_exists = Notification.objects.filter(
                recipient=self.manager_user, notification_type="REGULARIZATION_REQUEST"
            ).exists()
            self.assertFalse(notification_exists)


class LeaveRequestCancelTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company", hr_email="hr@test.com")
        self.employee_user = User.objects.create_user(
            username="employee_cancel",
            email="employee_cancel@test.com",
            password="password",
            role=User.Role.EMPLOYEE,
            company=self.company,
            must_change_password=False,
        )
        self.employee = Employee.objects.create(
            user=self.employee_user,
            company=self.company,
            designation="Developer",
            department="Engineering",
            badge_id="EMP002",
        )
        from employees.models import LeaveBalance

        self.balance, _ = LeaveBalance.objects.get_or_create(employee=self.employee)
        self.balance.casual_leave_allocated = 10
        self.balance.save()
        self.client = Client()
        self.client.login(username="employee_cancel@test.com", password="password")

    def test_cancel_active_or_future_leave_request(self):
        from datetime import timedelta

        from employees.models import LeaveRequest

        # Leave request in the future
        tomorrow = timezone.localdate() + timedelta(days=1)
        leave = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type="CL",
            start_date=tomorrow,
            end_date=tomorrow,
            status="PENDING",
        )
        self.assertFalse(leave.has_passed)

        # Cancel it
        response = self.client.post(f"/me/leaves/cancel/{leave.pk}/")
        self.assertEqual(response.status_code, 302)
        # Verify it is deleted (cancelled)
        self.assertFalse(LeaveRequest.objects.filter(pk=leave.pk).exists())

    def test_cancel_past_leave_request_fails(self):
        from datetime import timedelta

        from employees.models import LeaveRequest

        # Leave request in the past
        yesterday = timezone.localdate() - timedelta(days=1)
        leave = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type="CL",
            start_date=yesterday,
            end_date=yesterday,
            status="PENDING",
        )
        self.assertTrue(leave.has_passed)

        # Attempt to cancel it
        response = self.client.post(f"/me/leaves/cancel/{leave.pk}/")
        self.assertEqual(response.status_code, 302)
        # Verify it still exists
        self.assertTrue(LeaveRequest.objects.filter(pk=leave.pk).exists())


class MonthlyLeaveAccrualTestCase(TestCase):
    def setUp(self):
        from dateutil.relativedelta import relativedelta

        # Create two companies with unique slugs, primary_domains and email_domains
        self.company_a = Company.objects.create(
            name="Petabytz",
            slug="petabytz",
            primary_domain="petabytz.com",
            email_domain="petabytz.com",
            hr_email="hr_a@test.com",
        )
        self.company_b = Company.objects.create(
            name="Bluebix",
            slug="bluebix",
            primary_domain="bluebix.com",
            email_domain="bluebix.com",
            hr_email="hr_b@test.com",
        )

        # Create locations
        self.location_a = Location.objects.create(company=self.company_a, name="A Office", timezone="Asia/Kolkata")
        self.location_b = Location.objects.create(company=self.company_b, name="B Office", timezone="Asia/Kolkata")

        # Create company admin for Company A
        self.admin_user_a = User.objects.create_user(
            username="admin_a",
            email="admin_a@test.com",
            password="password",
            role=User.Role.COMPANY_ADMIN,
            company=self.company_a,
            must_change_password=False,
        )

        # Create active employee in Company A (probation completed)
        self.emp_user_a = User.objects.create_user(
            username="emp_a",
            email="emp_a@test.com",
            password="password",
            role=User.Role.EMPLOYEE,
            company=self.company_a,
            must_change_password=False,
        )
        self.emp_a = Employee.objects.create(
            user=self.emp_user_a,
            company=self.company_a,
            location=self.location_a,
            designation="Developer",
            date_of_joining=timezone.now().date() - relativedelta(months=4),
            badge_id="EMPA001",
        )

        # Create active employee in Company B (probation completed)
        self.emp_user_b = User.objects.create_user(
            username="emp_b",
            email="emp_b@test.com",
            password="password",
            role=User.Role.EMPLOYEE,
            company=self.company_b,
            must_change_password=False,
        )
        self.emp_b = Employee.objects.create(
            user=self.emp_user_b,
            company=self.company_b,
            location=self.location_b,
            designation="Developer",
            date_of_joining=timezone.now().date() - relativedelta(months=4),
            badge_id="EMPB002",
        )

        from employees.models import LeaveBalance

        self.balance_a, _ = LeaveBalance.objects.get_or_create(employee=self.emp_a)
        self.balance_a.sick_leave_allocated = 0.0
        self.balance_a.casual_leave_allocated = 0.0
        self.balance_a.save()

        self.balance_b, _ = LeaveBalance.objects.get_or_create(employee=self.emp_b)
        self.balance_b.combined_sick_casual_allocated = 0.0
        self.balance_b.save()

        self.client = Client()

    def test_run_monthly_accrual_filters_by_company(self):
        # Login as Admin of Company A
        self.client.login(username="admin_a@test.com", password="password")

        # Run monthly accrual
        response = self.client.post(
            "/employees/leave/configuration/accrue/", {"month": timezone.now().month, "year": timezone.now().year}
        )
        self.assertEqual(response.status_code, 302)

        # Refresh leave balances from DB
        self.balance_a.refresh_from_db()
        self.balance_b.refresh_from_db()

        # Company A (Petabytz) employee should have leaves accrued (+1 SL, +1 CL)
        self.assertEqual(self.balance_a.sick_leave_allocated, 1.0)
        self.assertEqual(self.balance_a.casual_leave_allocated, 1.0)

        # Company B (Bluebix) employee should have NO leaves accrued (remains 0)
        self.assertEqual(self.balance_b.combined_sick_casual_allocated, 0.0)

    def test_run_monthly_accrual_filters_by_location(self):
        from dateutil.relativedelta import relativedelta

        # Create second location for Company A
        location_a2 = Location.objects.create(company=self.company_a, name="A2 Office", timezone="Asia/Kolkata")

        # Create second active employee in Company A, in location_a2
        emp_user_a2 = User.objects.create_user(
            username="emp_a2",
            email="emp_a2@test.com",
            password="password",
            role=User.Role.EMPLOYEE,
            company=self.company_a,
            must_change_password=False,
        )
        emp_a2 = Employee.objects.create(
            user=emp_user_a2,
            company=self.company_a,
            location=location_a2,
            designation="Developer",
            date_of_joining=timezone.now().date() - relativedelta(months=4),
            badge_id="EMPA002",
        )
        from employees.models import LeaveBalance

        balance_a2, _ = LeaveBalance.objects.get_or_create(employee=emp_a2)
        balance_a2.sick_leave_allocated = 0.0
        balance_a2.casual_leave_allocated = 0.0
        balance_a2.save()

        # Login as Admin of Company A
        self.client.login(username="admin_a@test.com", password="password")

        # Run monthly accrual for location_a only
        month = timezone.now().month
        year = timezone.now().year
        response = self.client.post(
            "/employees/leave/configuration/accrue/", {"month": month, "year": year, "location_id": self.location_a.id}
        )
        self.assertEqual(response.status_code, 302)

        # Refresh from DB
        self.balance_a.refresh_from_db()
        balance_a2.refresh_from_db()

        # emp_a in location_a should have accrued
        self.assertEqual(self.balance_a.sick_leave_allocated, 1.0)
        # emp_a2 in location_a2 should NOT have accrued
        self.assertEqual(balance_a2.sick_leave_allocated, 0.0)

    def test_check_accrual_status_and_double_run(self):
        # Login as Admin of Company A
        self.client.login(username="admin_a@test.com", password="password")
        month = timezone.now().month
        year = timezone.now().year

        # Initially, check endpoint should say not already run
        response = self.client.get("/employees/leave/configuration/accrue/check/", {"month": month, "year": year})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["already_run"])

        # Run accrual first time
        response = self.client.post("/employees/leave/configuration/accrue/", {"month": month, "year": year})
        self.assertEqual(response.status_code, 302)

        # Check status endpoint now
        response = self.client.get("/employees/leave/configuration/accrue/check/", {"month": month, "year": year})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["already_run"])
        self.assertEqual(data["run_by"], self.admin_user_a.get_full_name() or self.admin_user_a.username)

        # Attempt to run accrual again without force
        response = self.client.post("/employees/leave/configuration/accrue/", {"month": month, "year": year})
        self.assertEqual(response.status_code, 302)
        self.balance_a.refresh_from_db()
        self.assertEqual(self.balance_a.sick_leave_allocated, 1.0)

        # Run accrual with force=true
        response = self.client.post(
            "/employees/leave/configuration/accrue/", {"month": month, "year": year, "force": "true"}
        )
        self.assertEqual(response.status_code, 302)
        self.balance_a.refresh_from_db()
        self.assertEqual(self.balance_a.sick_leave_allocated, 2.0)


class ManagerFilteringTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company", hr_email="hr@test.com")
        self.location = Location.objects.create(company=self.company, name="Main Office", timezone="Asia/Kolkata")

        # Current user (admin)
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="password",
            role=User.Role.COMPANY_ADMIN,
            company=self.company,
            must_change_password=False,
        )
        self.admin_employee = Employee.objects.create(
            user=self.admin_user, company=self.company, designation="Admin", department="HR", badge_id="ADM001"
        )

        # 1. Active manager
        self.active_mgr_user = User.objects.create_user(
            username="active_mgr",
            email="active_mgr@test.com",
            password="password",
            role=User.Role.MANAGER,
            company=self.company,
            must_change_password=False,
        )
        self.active_mgr_emp = Employee.objects.create(
            user=self.active_mgr_user,
            company=self.company,
            designation="Manager",
            department="Engineering",
            badge_id="MGR002",
        )

        # 2. Inactive manager (exited: is_active=False)
        self.inactive_mgr_user = User.objects.create_user(
            username="inactive_mgr",
            email="inactive_mgr@test.com",
            password="password",
            role=User.Role.MANAGER,
            company=self.company,
            is_active=False,
            must_change_password=False,
        )
        self.inactive_mgr_emp = Employee.objects.create(
            user=self.inactive_mgr_user,
            company=self.company,
            designation="Manager",
            department="Engineering",
            badge_id="MGR003",
            is_active=False,
            employment_status="TERMINATED",
        )

        # 3. Resigned manager (exited: employment_status="RESIGNED")
        self.resigned_mgr_user = User.objects.create_user(
            username="resigned_mgr",
            email="resigned_mgr@test.com",
            password="password",
            role=User.Role.MANAGER,
            company=self.company,
            must_change_password=False,
        )
        self.resigned_mgr_emp = Employee.objects.create(
            user=self.resigned_mgr_user,
            company=self.company,
            designation="Manager",
            department="Engineering",
            badge_id="MGR004",
            is_active=True,
            employment_status="RESIGNED",
        )

    def test_employee_creation_form_filters_out_exited_managers(self):
        from employees.forms import EmployeeCreationForm

        form = EmployeeCreationForm(user=self.admin_user)
        queryset = form.fields["manager"].queryset

        # The admin themselves and the active manager should be in the queryset.
        # The inactive and resigned managers should NOT be in the queryset.
        self.assertIn(self.active_mgr_user, queryset)
        self.assertIn(self.admin_user, queryset)
        self.assertNotIn(self.inactive_mgr_user, queryset)
        self.assertNotIn(self.resigned_mgr_user, queryset)

    def test_job_details_form_filters_out_exited_managers(self):
        from employees.multi_step_forms import JobDetailsForm

        form = JobDetailsForm(user=self.admin_user, company_id=self.company.id)
        queryset = form.fields["manager_selection"].queryset

        # The admin employee and the active manager employee should be in the queryset.
        # The inactive and resigned manager employees should NOT be in the queryset.
        self.assertIn(self.active_mgr_emp, queryset)
        self.assertIn(self.admin_employee, queryset)
        self.assertNotIn(self.inactive_mgr_emp, queryset)
        self.assertNotIn(self.resigned_mgr_emp, queryset)
