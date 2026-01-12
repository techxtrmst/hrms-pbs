"""
AI Attendance Intelligence Module
Analyzes attendance patterns and provides insights
"""

from datetime import timedelta
from django.utils import timezone
from employees.models import Attendance, Employee


class AttendanceIntelligence:
    """
    AI-powered attendance analysis and insights
    """

    @staticmethod
    def analyze_employee_patterns(employee, days=30):
        """
        Analyze attendance patterns for a specific employee
        Returns insights about late logins, early logouts, missed punches, etc.
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        attendances = (
            Attendance.objects.filter(
                employee=employee, date__gte=start_date, date__lte=end_date
            )
            .exclude(status="WEEKLY_OFF")
            .exclude(status="HOLIDAY")
        )

        total_days = attendances.count()
        if total_days == 0:
            return {
                "employee": employee,
                "period_days": days,
                "total_working_days": 0,
                "insights": [],
                "risk_level": "LOW",
                "score": 0,
            }

        # Count various patterns
        late_logins = attendances.filter(is_late=True).count()
        early_logouts = attendances.filter(is_early_departure=True).count()
        missed_clock_out = attendances.filter(
            clock_in__isnull=False, clock_out__isnull=True
        ).count()
        absences = attendances.filter(status="ABSENT").count()
        half_days = attendances.filter(status="HALF_DAY").count()

        # Calculate percentages
        late_percentage = (late_logins / total_days) * 100 if total_days > 0 else 0
        early_percentage = (early_logouts / total_days) * 100 if total_days > 0 else 0
        absence_percentage = (absences / total_days) * 100 if total_days > 0 else 0

        # Generate insights
        insights = []
        risk_score = 0

        # Late login pattern
        if late_logins >= 6:
            insights.append(
                {
                    "type": "WARNING",
                    "category": "Late Login",
                    "message": f"Employee is late {late_logins} times in {days} days ({late_percentage:.1f}%). Risk of LOP.",
                    "severity": "HIGH" if late_logins >= 10 else "MEDIUM",
                    "count": late_logins,
                }
            )
            risk_score += late_logins * 5
        elif late_logins >= 3:
            insights.append(
                {
                    "type": "INFO",
                    "category": "Late Login",
                    "message": f"Employee has {late_logins} late logins in the last {days} days.",
                    "severity": "LOW",
                    "count": late_logins,
                }
            )
            risk_score += late_logins * 2

        # Early logout pattern
        if early_logouts >= 5:
            insights.append(
                {
                    "type": "WARNING",
                    "category": "Early Logout",
                    "message": f"Frequent early logout detected ({early_logouts} times). May indicate disengagement.",
                    "severity": "MEDIUM",
                    "count": early_logouts,
                }
            )
            risk_score += early_logouts * 4

        # Missed clock-out behavior
        if missed_clock_out >= 3:
            insights.append(
                {
                    "type": "WARNING",
                    "category": "Missed Clock-Out",
                    "message": f"Employee forgot to clock out {missed_clock_out} times. Needs reminder.",
                    "severity": "MEDIUM",
                    "count": missed_clock_out,
                }
            )
            risk_score += missed_clock_out * 3

        # Absence pattern
        if absences >= 3:
            insights.append(
                {
                    "type": "ALERT",
                    "category": "Absences",
                    "message": f"High absence rate: {absences} days absent ({absence_percentage:.1f}%).",
                    "severity": "HIGH",
                    "count": absences,
                }
            )
            risk_score += absences * 8

        # Half day pattern
        if half_days >= 4:
            insights.append(
                {
                    "type": "INFO",
                    "category": "Half Days",
                    "message": f"{half_days} half days recorded in the last {days} days.",
                    "severity": "LOW",
                    "count": half_days,
                }
            )
            risk_score += half_days * 2

        # Check for Friday pattern (potential long weekend abuse)
        friday_absences = attendances.filter(
            date__week_day=6,  # Friday
            status="ABSENT",
        ).count()

        if friday_absences >= 2:
            insights.append(
                {
                    "type": "INFO",
                    "category": "Pattern",
                    "message": f"Employee tends to take leave on Fridays ({friday_absences} times).",
                    "severity": "LOW",
                    "count": friday_absences,
                }
            )

        # Determine overall risk level
        if risk_score >= 80:
            risk_level = "CRITICAL"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Add positive insights if performance is good
        if late_logins == 0 and absences == 0:
            insights.append(
                {
                    "type": "SUCCESS",
                    "category": "Performance",
                    "message": f"Excellent attendance! No late arrivals or absences in {days} days.",
                    "severity": "POSITIVE",
                    "count": 0,
                }
            )

        return {
            "employee": employee,
            "period_days": days,
            "total_working_days": total_days,
            "late_logins": late_logins,
            "early_logouts": early_logouts,
            "missed_clock_out": missed_clock_out,
            "absences": absences,
            "half_days": half_days,
            "late_percentage": round(late_percentage, 1),
            "early_percentage": round(early_percentage, 1),
            "absence_percentage": round(absence_percentage, 1),
            "insights": insights,
            "risk_level": risk_level,
            "risk_score": min(risk_score, 100),  # Cap at 100
        }

    @staticmethod
    def get_company_insights(company, days=30):
        """
        Get attendance insights for entire company
        """
        employees = Employee.objects.filter(company=company, is_active=True)

        all_insights = []
        high_risk_employees = []

        for emp in employees:
            analysis = AttendanceIntelligence.analyze_employee_patterns(emp, days)

            if analysis["risk_level"] in ["HIGH", "CRITICAL"]:
                high_risk_employees.append(
                    {
                        "employee": emp,
                        "risk_level": analysis["risk_level"],
                        "risk_score": analysis["risk_score"],
                        "insights": analysis["insights"],
                    }
                )

            all_insights.append(analysis)

        # Sort by risk score
        high_risk_employees.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "total_employees": employees.count(),
            "high_risk_count": len(high_risk_employees),
            "high_risk_employees": high_risk_employees,
            "all_insights": all_insights,
        }

    @staticmethod
    def check_location_mismatch(employee, days=7):
        """
        Detect location mismatches (WFH vs Office)
        This is a placeholder - implement based on your location tracking logic
        """
        # TODO: Implement location-based analysis
        # This would require comparing expected location with actual location
        return {"has_mismatch": False, "mismatch_count": 0, "details": []}
