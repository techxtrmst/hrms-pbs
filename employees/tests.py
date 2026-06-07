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

            # Check if RegularizationRequest with change_type WEEK_OFF_WORK was created
            reg_req = RegularizationRequest.objects.filter(
                employee=self.employee, date=monday_date, change_type="WEEK_OFF_WORK"
            ).first()
            self.assertIsNotNone(reg_req)
            self.assertEqual(reg_req.status, "PENDING")
            self.assertEqual(reg_req.check_in, mock_now.time())

            # Check if Notification was created for manager
            notification = Notification.objects.filter(
                recipient=self.manager_user, notification_type="REGULARIZATION_REQUEST"
            ).first()
            self.assertIsNotNone(notification)
            self.assertIn("clocked in on their week-off", notification.message)

            # Let's test clock out updates the check_out time on the request
            mock_checkout_now = tz.localize(timezone.datetime(2026, 6, 8, 18, 0, 0))
            with patch("django.utils.timezone.now", return_value=mock_checkout_now):
                response_out = self.client.post(
                    "/employees/api/clock-out/",
                    {"latitude": 12.9716, "longitude": 77.5946, "accuracy": 10, "force_clockout": True},
                    content_type="application/json",
                )

                self.assertEqual(response_out.status_code, 200)

                # Verify request check_out is updated
                reg_req.refresh_from_db()
                self.assertEqual(reg_req.check_out, mock_checkout_now.time())

        # Test Rejecting the request updates the Attendance record status to WEEKLY_OFF
        # Let's log in as the manager
        self.client.login(username="manager@test.com", password="password")
        response_reject = self.client.post(
            f"/employees/regularization/{reg_req.pk}/reject/", {"rejection_reason": "Not approved"}
        )
        self.assertEqual(response_reject.status_code, 302)

        # Verify the request status is REJECTED
        reg_req.refresh_from_db()
        self.assertEqual(reg_req.status, "REJECTED")
        self.assertEqual(reg_req.manager_comment, "Not approved")

        # Verify the Attendance status is WEEKLY_OFF
        attendance.refresh_from_db()
        self.assertEqual(attendance.status, "WEEKLY_OFF")
