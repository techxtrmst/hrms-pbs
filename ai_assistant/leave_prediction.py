"""
AI Leave Prediction & Auto-Suggestions Module
Predicts leave patterns and provides team planning insights
"""

import calendar
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from employees.models import Employee, LeaveRequest


class LeavePrediction:
    """
    AI-powered leave prediction and team planning
    """

    @staticmethod
    def analyze_leave_patterns(employee, months=6):
        """
        Analyze employee's leave taking patterns
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=months * 30)

        leaves = LeaveRequest.objects.filter(employee=employee, start_date__gte=start_date, status="APPROVED")

        total_leaves = leaves.count()
        if total_leaves == 0:
            return {
                "employee": employee,
                "total_leaves": 0,
                "patterns": [],
                "predictions": [],
            }

        # Analyze day-of-week patterns
        day_frequency = defaultdict(int)
        for leave in leaves:
            current_date = leave.start_date
            while current_date <= leave.end_date:
                day_name = calendar.day_name[current_date.weekday()]
                day_frequency[day_name] += 1
                current_date += timedelta(days=1)

        # Find most common day
        patterns = []
        if day_frequency:
            most_common_day = max(day_frequency, key=day_frequency.get)
            if day_frequency[most_common_day] >= 3:
                patterns.append(
                    {
                        "type": "DAY_PREFERENCE",
                        "message": f"Employee usually takes leave on {most_common_day}s ({day_frequency[most_common_day]} times)",
                        "day": most_common_day,
                        "frequency": day_frequency[most_common_day],
                    }
                )

        # Analyze month patterns
        month_frequency = defaultdict(int)
        for leave in leaves:
            month_name = calendar.month_name[leave.start_date.month]
            month_frequency[month_name] += 1

        if month_frequency:
            most_common_month = max(month_frequency, key=month_frequency.get)
            if month_frequency[most_common_month] >= 2:
                patterns.append(
                    {
                        "type": "MONTH_PREFERENCE",
                        "message": f"Higher leave frequency in {most_common_month} ({month_frequency[most_common_month]} times)",
                        "month": most_common_month,
                        "frequency": month_frequency[most_common_month],
                    }
                )

        # Check for festival/holiday clustering
        # Get upcoming holidays and predict leave clustering
        predictions = LeavePrediction._predict_upcoming_leaves(employee, day_frequency)

        # Calculate average leave duration
        total_days = sum(leave.total_days for leave in leaves)
        avg_duration = total_days / total_leaves if total_leaves > 0 else 0

        return {
            "employee": employee,
            "total_leaves": total_leaves,
            "total_days": total_days,
            "avg_duration": round(avg_duration, 1),
            "day_frequency": dict(day_frequency),
            "month_frequency": dict(month_frequency),
            "patterns": patterns,
            "predictions": predictions,
        }

    @staticmethod
    def _predict_upcoming_leaves(employee, day_frequency):
        """
        Predict potential upcoming leaves based on patterns
        """
        predictions = []
        today = timezone.now().date()

        # Check next 30 days
        for i in range(1, 31):
            future_date = today + timedelta(days=i)
            day_name = calendar.day_name[future_date.weekday()]

            # If this day has high frequency in past
            if day_name in day_frequency and day_frequency[day_name] >= 3:
                predictions.append(
                    {
                        "date": future_date,
                        "day": day_name,
                        "probability": "HIGH" if day_frequency[day_name] >= 5 else "MEDIUM",
                        "reason": f"Employee frequently takes leave on {day_name}s",
                    }
                )

        return predictions[:5]  # Return top 5 predictions

    @staticmethod
    def predict_team_shortage(company, department=None, days_ahead=14):
        """
        Predict team shortage based on approved and pending leaves
        """
        today = timezone.now().date()
        end_date = today + timedelta(days=days_ahead)

        # Get all employees
        employees = Employee.objects.filter(company=company, is_active=True)
        if department:
            employees = employees.filter(department=department)

        total_employees = employees.count()

        # Get all leaves in the period
        leaves = LeaveRequest.objects.filter(
            employee__company=company,
            employee__is_active=True,
            status__in=["APPROVED", "PENDING"],
            start_date__lte=end_date,
            end_date__gte=today,
        )

        if department:
            leaves = leaves.filter(employee__department=department)

        # Calculate daily shortage
        daily_shortage = {}
        for i in range(days_ahead + 1):
            check_date = today + timedelta(days=i)

            # Count employees on leave on this date
            on_leave = (
                leaves.filter(start_date__lte=check_date, end_date__gte=check_date)
                .values("employee")
                .distinct()
                .count()
            )

            shortage_percentage = (on_leave / total_employees * 100) if total_employees > 0 else 0

            daily_shortage[check_date.strftime("%Y-%m-%d")] = {
                "date": check_date,
                "on_leave": on_leave,
                "available": total_employees - on_leave,
                "shortage_percentage": round(shortage_percentage, 1),
                "risk_level": LeavePrediction._get_shortage_risk_level(shortage_percentage),
            }

        # Find critical days (>30% shortage)
        critical_days = [data for date, data in daily_shortage.items() if data["shortage_percentage"] > 30]

        return {
            "total_employees": total_employees,
            "period_start": today,
            "period_end": end_date,
            "daily_shortage": daily_shortage,
            "critical_days": critical_days,
            "has_critical_shortage": len(critical_days) > 0,
        }

    @staticmethod
    def _get_shortage_risk_level(percentage):
        """
        Determine risk level based on shortage percentage
        """
        if percentage >= 50:
            return "CRITICAL"
        elif percentage >= 30:
            return "HIGH"
        elif percentage >= 20:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def get_leave_recommendations(employee):
        """
        Provide smart recommendations for leave planning
        """
        recommendations = []

        # Check leave balance
        try:
            balance = employee.leave_balance

            # Recommend using expiring leaves
            if hasattr(balance, "earned_leave_balance") and balance.earned_leave_balance > 15:
                recommendations.append(
                    {
                        "type": "BALANCE_HIGH",
                        "priority": "MEDIUM",
                        "message": f"You have {balance.earned_leave_balance} Earned Leaves. Consider planning a vacation.",
                        "action": "Plan Leave",
                    }
                )

            # Warn about low balance
            if hasattr(balance, "casual_leave_balance") and balance.casual_leave_balance < 2:
                recommendations.append(
                    {
                        "type": "BALANCE_LOW",
                        "priority": "HIGH",
                        "message": f"Only {balance.casual_leave_balance} Casual Leaves remaining. Use wisely.",
                        "action": "Monitor Usage",
                    }
                )

            # Check comp-off expiry (if applicable)
            if hasattr(balance, "comp_off_balance") and balance.comp_off_balance > 0:
                recommendations.append(
                    {
                        "type": "COMP_OFF",
                        "priority": "MEDIUM",
                        "message": f"You have {balance.comp_off_balance} Comp-Off(s). Remember to use them before expiry.",
                        "action": "Use Comp-Off",
                    }
                )

        except:
            pass

        return recommendations

    @staticmethod
    def analyze_festival_clustering(company, days_ahead=60):
        """
        Analyze leave clustering around holidays/festivals
        This is a placeholder - implement based on your holiday calendar
        """
        # TODO: Integrate with holiday calendar
        # Predict leave clustering around holidays

        return {"upcoming_holidays": [], "predicted_clusters": []}
