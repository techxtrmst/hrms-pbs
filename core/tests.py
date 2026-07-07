from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from companies.models import Company
from employees.models import Employee, LeaveRequest

User = get_user_model()


class LeaveRequestManagerScopingTestCase(TestCase):
    def setUp(self):
        # Create company
        self.company = Company.objects.create(name="Scope Test Company", hr_email="hr@scopetest.com")

        # Create two managers
        self.manager1_user = User.objects.create_user(
            username="manager1",
            email="manager1@scopetest.com",
            password="password",
            role=User.Role.MANAGER,
            company=self.company,
            must_change_password=False,
        )
        self.manager1_emp = Employee.objects.create(
            user=self.manager1_user,
            company=self.company,
            designation="Manager 1",
            department="Engineering",
            badge_id="MGR01",
        )

        self.manager2_user = User.objects.create_user(
            username="manager2",
            email="manager2@scopetest.com",
            password="password",
            role=User.Role.MANAGER,
            company=self.company,
            must_change_password=False,
        )
        self.manager2_emp = Employee.objects.create(
            user=self.manager2_user, company=self.company, designation="Manager 2", department="Sales", badge_id="MGR02"
        )

        # Create an admin
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@scopetest.com",
            password="password",
            role=User.Role.COMPANY_ADMIN,
            company=self.company,
            must_change_password=False,
        )

        # Create employee reporting to manager1
        self.emp1_user = User.objects.create_user(
            username="employee1",
            email="employee1@scopetest.com",
            password="password",
            role=User.Role.EMPLOYEE,
            company=self.company,
            must_change_password=False,
        )
        self.emp1 = Employee.objects.create(
            user=self.emp1_user,
            company=self.company,
            manager=self.manager1_user,
            designation="Developer",
            department="Engineering",
            badge_id="EMP01",
        )

        # Create employee reporting to manager2
        self.emp2_user = User.objects.create_user(
            username="employee2",
            email="employee2@scopetest.com",
            password="password",
            role=User.Role.EMPLOYEE,
            company=self.company,
            must_change_password=False,
        )
        self.emp2 = Employee.objects.create(
            user=self.emp2_user,
            company=self.company,
            manager=self.manager2_user,
            designation="Sales Executive",
            department="Sales",
            badge_id="EMP02",
        )

        # Initialize leave balances if post_save signals don't automatically create them
        from employees.models import LeaveBalance

        self.balance1, _ = LeaveBalance.objects.get_or_create(employee=self.emp1)
        self.balance1.casual_leave_allocated = 10
        self.balance1.save()

        self.balance2, _ = LeaveBalance.objects.get_or_create(employee=self.emp2)
        self.balance2.casual_leave_allocated = 10
        self.balance2.save()

        # Create a leave request for employee1 (managed by manager1)
        self.leave1 = LeaveRequest.objects.create(
            employee=self.emp1,
            leave_type="CL",
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
            status="PENDING",
        )

        # Create a leave request for employee2 (managed by manager2)
        self.leave2 = LeaveRequest.objects.create(
            employee=self.emp2,
            leave_type="CL",
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
            status="PENDING",
        )

        self.client = Client()

    def test_manager_sees_only_own_team_leave_requests(self):
        # Login as manager 1
        self.client.login(username="manager1@scopetest.com", password="password")
        response = self.client.get("/leaves/requests/")
        self.assertEqual(response.status_code, 200)

        # Manager 1 should see leave1 but not leave2
        leave_requests = response.context["leave_requests"]
        self.assertIn(self.leave1, leave_requests)
        self.assertNotIn(self.leave2, leave_requests)

    def test_admin_sees_all_company_leave_requests(self):
        # Login as admin
        self.client.login(username="admin@scopetest.com", password="password")
        response = self.client.get("/leaves/requests/")
        self.assertEqual(response.status_code, 200)

        # Admin should see both leave1 and leave2
        leave_requests = response.context["leave_requests"]
        self.assertIn(self.leave1, leave_requests)
        self.assertIn(self.leave2, leave_requests)

    def test_manager_cannot_approve_other_team_leave_request(self):
        # Login as manager 1
        self.client.login(username="manager1@scopetest.com", password="password")

        # Try to approve manager 2's employee request (leave2)
        response = self.client.post(
            "/leaves/requests/",
            {
                "action": "approve",
                "leave_id": self.leave2.id,
                "approval_type": "FULL",
                "admin_comment": "Testing manager 1 approving manager 2 employee",
            },
        )
        # It redirects to leave_requests list
        self.assertEqual(response.status_code, 302)

        # The request should still be pending and not approved
        self.leave2.refresh_from_db()
        self.assertEqual(self.leave2.status, "PENDING")

    def test_manager_can_approve_own_team_leave_request(self):
        # Login as manager 1
        self.client.login(username="manager1@scopetest.com", password="password")

        # Approve own employee request (leave1)
        response = self.client.post(
            "/leaves/requests/",
            {"action": "approve", "leave_id": self.leave1.id, "approval_type": "FULL", "admin_comment": "Approved"},
        )
        self.assertEqual(response.status_code, 302)

        # The request should be approved
        self.leave1.refresh_from_db()
        self.assertEqual(self.leave1.status, "APPROVED")
