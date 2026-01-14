"""
AI Smart Notifications & Alerts Module
Automated intelligent notifications for various HR scenarios
"""

from datetime import timedelta
from django.utils import timezone
from employees.models import Employee, Attendance, LeaveRequest
from loguru import logger


class SmartNotifications:
    """
    AI-powered smart notifications and alerts
    """

    @staticmethod
    def check_missed_clock_out(employee):
        """
        Check if employee forgot to clock out today
        """
        today = timezone.now().date()

        try:
            attendance = Attendance.objects.get(employee=employee, date=today)

            # If clocked in but not clocked out, and it's past work hours
            if attendance.clock_in and not attendance.clock_out:
                clock_in_time = attendance.clock_in
                hours_since_clock_in = (
                    timezone.now() - clock_in_time
                ).total_seconds() / 3600

                # If more than 10 hours since clock in
                if hours_since_clock_in > 10:
                    return {
                        "alert": True,
                        "type": "MISSED_CLOCK_OUT",
                        "severity": "MEDIUM",
                        "message": "You have not clocked out today. Please confirm.",
                        "clock_in_time": clock_in_time,
                        "hours_elapsed": round(hours_since_clock_in, 1),
                    }
        except Attendance.DoesNotExist:
            pass

        return {"alert": False}

    @staticmethod
    def check_pending_approvals(manager):
        """
        Check for pending leave approvals for a manager
        """
        try:
            # Get employees reporting to this manager
            team_members = Employee.objects.filter(
                manager=manager.employee_profile, is_active=True
            )

            pending_leaves = LeaveRequest.objects.filter(
                employee__in=team_members, status="PENDING"
            ).order_by("created_at")

            if pending_leaves.exists():
                # Check for old pending requests (>2 days)
                old_pending = pending_leaves.filter(
                    created_at__lt=timezone.now() - timedelta(days=2)
                )

                return {
                    "alert": True,
                    "type": "PENDING_APPROVALS",
                    "severity": "HIGH" if old_pending.exists() else "MEDIUM",
                    "message": f"You have {pending_leaves.count()} pending leave approval(s).",
                    "total_pending": pending_leaves.count(),
                    "old_pending": old_pending.count(),
                    "pending_requests": pending_leaves,
                }
        except Exception as e:
            logger.debug("Error checking manager pending approvals", error=str(e))

        return {"alert": False}

    @staticmethod
    def check_lop_threshold(employee):
        """
        Check if employee is nearing LOP threshold
        """
        try:
            balance = employee.leave_balance

            # Check if any balance is negative or near zero
            warnings = []

            if balance.casual_leave_balance() < 0:
                warnings.append(
                    {
                        "type": "NEGATIVE_BALANCE",
                        "leave_type": "Casual Leave",
                        "balance": balance.casual_leave_balance(),
                        "message": f"Your Casual Leave balance is negative ({balance.casual_leave_balance()}). Future leaves will be LOP.",
                    }
                )
            elif balance.casual_leave_balance() < 1:
                warnings.append(
                    {
                        "type": "LOW_BALANCE",
                        "leave_type": "Casual Leave",
                        "balance": balance.casual_leave_balance(),
                        "message": f"Only {balance.casual_leave_balance()} Casual Leave remaining.",
                    }
                )

            if balance.sick_leave_balance() < 0:
                warnings.append(
                    {
                        "type": "NEGATIVE_BALANCE",
                        "leave_type": "Sick Leave",
                        "balance": balance.sick_leave_balance(),
                        "message": f"Your Sick Leave balance is negative ({balance.sick_leave_balance()}). Future leaves will be LOP.",
                    }
                )

            if warnings:
                return {
                    "alert": True,
                    "type": "LOP_THRESHOLD",
                    "severity": "HIGH"
                    if any(w["type"] == "NEGATIVE_BALANCE" for w in warnings)
                    else "MEDIUM",
                    "warnings": warnings,
                }
        except:
            pass

        return {"alert": False}

    @staticmethod
    def check_contract_expiry(employee, days_ahead=30):
        """
        Check if employee's contract or probation is expiring soon
        """
        alerts = []
        today = timezone.now().date()

        # Check probation end only if the field exists
        if hasattr(employee, "probation_end_date") and employee.probation_end_date:
            days_to_end = (employee.probation_end_date - today).days

            if 0 < days_to_end <= days_ahead:
                alerts.append(
                    {
                        "type": "PROBATION_ENDING",
                        "date": employee.probation_end_date,
                        "days_remaining": days_to_end,
                        "message": f"Probation period ends in {days_to_end} days ({employee.probation_end_date}).",
                        "action_required": "Confirmation or extension needed",
                    }
                )

        # Check contract end (if applicable)
        # TODO: Add contract end date field to Employee model if needed

        if alerts:
            return {
                "alert": True,
                "type": "CONTRACT_EXPIRY",
                "severity": "HIGH"
                if any(a["days_remaining"] <= 7 for a in alerts)
                else "MEDIUM",
                "alerts": alerts,
            }

        return {"alert": False}

    @staticmethod
    def check_late_login_pattern(employee, threshold=3):
        """
        Alert if employee has been late multiple times recently
        """
        # Check last 7 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)

        late_count = Attendance.objects.filter(
            employee=employee, date__gte=start_date, date__lte=end_date, is_late=True
        ).count()

        if late_count >= threshold:
            return {
                "alert": True,
                "type": "LATE_LOGIN_PATTERN",
                "severity": "MEDIUM",
                "message": f"You have been late {late_count} times in the last 7 days.",
                "late_count": late_count,
                "action": "Please ensure timely attendance to avoid LOP.",
            }

        return {"alert": False}

    @staticmethod
    def get_all_alerts_for_employee(employee):
        """
        Get all active alerts for an employee
        """
        alerts = []

        # Check missed clock out
        missed_clock_out = SmartNotifications.check_missed_clock_out(employee)
        if missed_clock_out["alert"]:
            alerts.append(missed_clock_out)

        # Check LOP threshold
        lop_threshold = SmartNotifications.check_lop_threshold(employee)
        if lop_threshold["alert"]:
            alerts.append(lop_threshold)

        # Check contract/probation expiry
        contract_expiry = SmartNotifications.check_contract_expiry(employee)
        if contract_expiry["alert"]:
            alerts.append(contract_expiry)

        # Check late login pattern
        late_pattern = SmartNotifications.check_late_login_pattern(employee)
        if late_pattern["alert"]:
            alerts.append(late_pattern)

        return alerts

    @staticmethod
    def get_all_alerts_for_manager(manager):
        """
        Get all active alerts for a manager
        """
        alerts = []

        # Check pending approvals
        pending_approvals = SmartNotifications.check_pending_approvals(manager)
        if pending_approvals["alert"]:
            alerts.append(pending_approvals)

        # Check team members' contract expiry
        try:
            team_members = Employee.objects.filter(
                manager=manager.employee_profile, is_active=True
            )

            for member in team_members:
                contract_alert = SmartNotifications.check_contract_expiry(
                    member, days_ahead=15
                )
                if contract_alert["alert"]:
                    contract_alert["employee"] = member
                    alerts.append(contract_alert)
        except:
            pass

        return alerts

    @staticmethod
    def send_notification_email(user, alert):
        """
        Send email notification for an alert
        This is a placeholder - integrate with your email system
        """
        # TODO: Implement email sending logic
        # Use your existing email_utils.py
        pass

    @staticmethod
    def generate_daily_digest(employee):
        """
        Generate a daily digest of important information
        """
        today = timezone.now().date()

        digest = {
            "date": today,
            "employee": employee,
            "alerts": SmartNotifications.get_all_alerts_for_employee(employee),
            "summary": {},
        }

        # Add attendance summary
        try:
            attendance = Attendance.objects.get(employee=employee, date=today)
            digest["summary"]["attendance"] = {
                "status": attendance.status,
                "clock_in": attendance.clock_in,
                "clock_out": attendance.clock_out,
            }
        except:
            digest["summary"]["attendance"] = None

        # Add leave balance
        try:
            balance = employee.leave_balance
            digest["summary"]["leave_balance"] = {
                "casual": balance.casual_leave_balance(),
                "sick": balance.sick_leave_balance(),
                "earned": balance.earned_leave_balance(),
            }
        except:
            digest["summary"]["leave_balance"] = None

        return digest
