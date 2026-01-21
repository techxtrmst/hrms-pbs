"""
AI-powered utilities for HRMS
1. Attrition Risk Prediction
2. HR Policy Chatbot
3. Resume Parser
"""

import re
from datetime import datetime, timedelta

import openai
from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from ai_assistant.models import AttritionRisk
from employees.models import Attendance, Employee, LeaveRequest


class AttritionPredictor:
    """
    Predicts employee attrition risk based on behavioral patterns
    """

    @staticmethod
    def calculate_risk_score(employee):
        """
        Calculate attrition risk score (0-100) based on multiple factors
        """
        score = 0
        factors = {}

        # Get data for last 3 months
        three_months_ago = timezone.now() - timedelta(days=90)

        # Factor 1: Frequent Sick Leaves (0-25 points)
        sick_leaves = LeaveRequest.objects.filter(
            employee=employee,
            leave_type="SL",
            status="APPROVED",
            created_at__gte=three_months_ago,
        ).count()

        if sick_leaves >= 5:
            sick_leave_score = 25
        elif sick_leaves >= 3:
            sick_leave_score = 15
        elif sick_leaves >= 1:
            sick_leave_score = 5
        else:
            sick_leave_score = 0

        score += sick_leave_score
        factors["sick_leaves"] = {
            "count": sick_leaves,
            "score": sick_leave_score,
            "description": f"{sick_leaves} sick leaves in last 3 months",
        }

        # Factor 2: Late Arrivals (0-25 points)
        late_arrivals = Attendance.objects.filter(
            employee=employee, is_late=True, date__gte=three_months_ago.date()
        ).count()

        if late_arrivals >= 10:
            late_score = 25
        elif late_arrivals >= 5:
            late_score = 15
        elif late_arrivals >= 2:
            late_score = 5
        else:
            late_score = 0

        score += late_score
        factors["late_arrivals"] = {
            "count": late_arrivals,
            "score": late_score,
            "description": f"{late_arrivals} late arrivals in last 3 months",
        }

        # Factor 3: Missing Punches (0-20 points)
        missing_punches = Attendance.objects.filter(
            employee=employee, status="MISSING_PUNCH", date__gte=three_months_ago.date()
        ).count()

        if missing_punches >= 8:
            missing_score = 20
        elif missing_punches >= 4:
            missing_score = 12
        elif missing_punches >= 2:
            missing_score = 5
        else:
            missing_score = 0

        score += missing_score
        factors["missing_punches"] = {
            "count": missing_punches,
            "score": missing_score,
            "description": f"{missing_punches} missing punches in last 3 months",
        }

        # Factor 4: Absences (0-20 points)
        absences = Attendance.objects.filter(
            employee=employee, status="ABSENT", date__gte=three_months_ago.date()
        ).count()

        if absences >= 5:
            absence_score = 20
        elif absences >= 3:
            absence_score = 12
        elif absences >= 1:
            absence_score = 5
        else:
            absence_score = 0

        score += absence_score
        factors["absences"] = {
            "count": absences,
            "score": absence_score,
            "description": f"{absences} absences in last 3 months",
        }

        # Factor 5: Tenure (0-10 points - new employees are higher risk)
        if employee.date_of_joining:
            tenure_days = (timezone.now().date() - employee.date_of_joining).days
            if tenure_days < 90:  # Less than 3 months
                tenure_score = 10
            elif tenure_days < 180:  # Less than 6 months
                tenure_score = 5
            else:
                tenure_score = 0
        else:
            tenure_score = 0

        score += tenure_score
        factors["tenure"] = {
            "days": tenure_days if employee.date_of_joining else 0,
            "score": tenure_score,
            "description": f"Tenure: {tenure_days if employee.date_of_joining else 0} days",
        }

        # Determine risk level
        if score >= 70:
            risk_level = "CRITICAL"
        elif score >= 50:
            risk_level = "HIGH"
        elif score >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "score": min(score, 100),  # Cap at 100
            "risk_level": risk_level,
            "factors": factors,
        }


class HRChatbot:
    """
    Friendly, conversational HR assistant that speaks naturally and helps employees
    """

    @staticmethod
    def get_response(question, employee, role="EMPLOYEE", request=None):
        """
        Process user question and return friendly, conversational response
        """
        question_lower = question.lower().strip()
        user_name = employee.user.first_name or employee.user.username

        # 1. Critical UI Actions - Keep these rule-based to ensure UI widgets (buttons) render correctly
        # Clock In
        if any(w in question_lower for w in ["clock in", "clock-in", "clockin", "punch in", "check in"]):
            return HRChatbot._handle_clock_in(employee, user_name)

        # Clock Out
        if any(w in question_lower for w in ["clock out", "clock-out", "clockout", "punch out", "check out"]):
            return HRChatbot._handle_clock_out(employee, user_name)

        # Apply Leave UI
        if any(
            phrase in question_lower
            for phrase in [
                "apply sick leave",
                "take sick leave",
                "sick leave",
                "apply sl",
            ]
        ):
            return HRChatbot._handle_leave_application(employee, user_name, "SL")

        if any(
            phrase in question_lower
            for phrase in [
                "apply casual leave",
                "take casual leave",
                "casual leave",
                "apply cl",
            ]
        ):
            return HRChatbot._handle_leave_application(employee, user_name, "CL")

        if any(
            phrase in question_lower
            for phrase in [
                "apply earned leave",
                "take earned leave",
                "earned leave",
                "apply el",
            ]
        ):
            return HRChatbot._handle_leave_application(employee, user_name, "EL")

        # General Apply Leave UI
        if (
            any(phrase in question_lower for phrase in ["apply leave", "request leave", "book leave"])
            and "balance" not in question_lower
        ):
            return {
                "answer": f"Sure, {user_name}! 📝\n\nWhich type of leave would you like to apply?\n\n🏥 **Sick Leave (SL)**\n🌴 **Casual Leave (CL)**\n✈️ **Earned Leave (EL)**",
                "type": "leave_options",
                "action": {
                    "type": "quick_replies",
                    "options": [
                        {"label": "Sick Leave", "value": "apply sick leave"},
                        {"label": "Casual Leave", "value": "apply casual leave"},
                        {"label": "Earned Leave", "value": "apply earned leave"},
                    ],
                },
            }

        # 3. Critical Data Actions (Must happen before AI)
        # Context-Aware "Yes" Handler (For Rule-Based & AI)
        if question_lower in ["yes", "yeah", "sure", "yup", "ok", "okay", "please"]:
            try:
                from ai_assistant.models import ChatMessage

                # Get last 3 bot messages to find context (in case of intervening notifications)
                last_msgs = ChatMessage.objects.filter(user=employee.user).order_by("-timestamp")[:3]

                for msg in last_msgs:
                    last_response = msg.bot_response

                    # 1. Finance / Payslip Context
                    if ("Finance" in last_response or "payslip" in last_response) and (
                        "finding it" in last_response or "download" in last_response
                    ):
                        return {
                            "answer": f"Here is the direct link, {user_name}! 🔗\n\n[Go to My Finance](/me/finance/)",
                            "type": "navigation",
                        }

                    # 2. Profile Context
                    if ("Profile" in last_response or "personal detail" in last_response) and (
                        "finding it" in last_response or "update" in last_response
                    ):
                        return {
                            "answer": f"Here is the direct link to your profile, {user_name}! 🔗\n\n[Go to My Profile](/me/profile/)",
                            "type": "navigation",
                        }

                    # 3. Generic Navigation Context (checks for breadcrumbs like Me -> X)
                    if "Need help finding it?" in last_response or "finding it" in last_response:
                        # Fallback for Policies
                        if "Policies" in last_response:
                            return {
                                "answer": "Here is the link to Policies:\n[Open Policies](/me/policy/)",
                                "type": "navigation",
                            }

            except Exception as e:
                print(f"Error in context handler: {e}")

        # Approve/Reject Leave
        if "approve leave" in question_lower or "reject leave" in question_lower:
            return HRChatbot._handle_approval_action(question_lower, employee, user_name)

        # Configuration Actions (Admin Only)
        if (role == "COMPANY_ADMIN" or employee.user.is_superuser) and "add holiday" in question_lower:
            response = HRChatbot._handle_configuration_action(question_lower, employee, user_name)
            if response:
                return response

        # 4. Role-Specific High-Priority Intent Matchers (Check before AI for precise navigation)
        if role == "COMPANY_ADMIN" or employee.user.is_superuser:
            resp = HRChatbot._handle_admin_query(question_lower, employee, user_name, request)
            if resp:
                return resp

        if role in ["MANAGER", "COMPANY_ADMIN"] or employee.user.is_superuser:
            resp = HRChatbot._handle_manager_query(question_lower, employee, user_name, request)
            if resp:
                return resp

        # 5. AI Intelligence Layer
        # If OpenAI key is configured, use it for all other queries
        if getattr(settings, "OPENAI_API_KEY", None):
            return HRChatbot._get_llm_response(question, employee, role, request)

        # 3. Legacy Rule-Based Fallback (if no AI key)
        # Greetings
        if (
            any(
                greeting in question_lower
                for greeting in [
                    "hello",
                    "hi",
                    "hey",
                    "good morning",
                    "good afternoon",
                    "good evening",
                ]
            )
            and len(question_lower) < 20
        ):
            return HRChatbot._get_greeting_response(user_name, role)

        # Thanks
        if any(thanks in question_lower for thanks in ["thank", "thanks", "appreciate"]):
            return {
                "answer": f"You're welcome, {user_name}! 😊\n\nIs there anything else I can help you with?",
                "type": "acknowledgment",
            }

        # Routing based on Role (Legacy)
        if role == "COMPANY_ADMIN":
            response = HRChatbot._handle_admin_query(question_lower, employee, user_name, request)
            if response:
                return response
            response = HRChatbot._handle_manager_query(question_lower, employee, user_name, request)
            if response:
                return response

        elif role == "MANAGER":
            response = HRChatbot._handle_manager_query(question_lower, employee, user_name, request)
            if response:
                return response

        # Fallback for everyone
        response = HRChatbot._handle_employee_query(question_lower, employee, user_name, request)
        if response:
            return response

        return HRChatbot._get_fallback_response(user_name, role)

    @staticmethod
    def _get_llm_response(question, employee, role, request):
        """
        Generate response using OpenAI with context-aware RAG
        """
        try:
            from ai_assistant.models import ChatMessage
            from companies.models import Holiday
            from employees.models import HandbookSection, Payslip, PolicySection

            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

            # --- 1. Handle Context-Aware "Yes" ---
            # If user says "yes" or similar, check previous bot message to infer action
            if question.lower().strip() in ["yes", "yeah", "yup", "sure", "ok", "okay"]:
                last_msg = ChatMessage.objects.filter(user=employee.user).order_by("-timestamp").last()
                if last_msg:
                    # Check if last bot message was about leave balance
                    if "Need to apply for leave?" in last_msg.bot_response:
                        return {
                            "answer": "Great! Please choose the leave type below: 👇",
                            "type": "leave_options",
                            "action": {
                                "type": "quick_replies",
                                "options": [
                                    {"label": "Sick Leave", "value": "apply sick leave"},
                                    {"label": "Casual Leave", "value": "apply casual leave"},
                                    {"label": "Earned Leave", "value": "apply earned leave"},
                                ],
                            },
                        }
                    # Check if last bot message was about clocking in
                    if "Clock In" in last_msg.bot_response and "clocked in" not in last_msg.bot_response:
                        return HRChatbot._handle_clock_in(employee, employee.user.first_name)

                    # Check if last bot message was about clocking out
                    if "Clock Out" in last_msg.bot_response:
                        return HRChatbot._handle_clock_out(employee, employee.user.first_name)

            # --- 2. Gather Context for LLM ---
            context_data = []

            # Employee Profile
            profile_info = f"""
            User: {employee.user.get_full_name()} (ID: {employee.badge_id})
            Designation: {employee.designation}
            Department: {employee.department}
            Location: {employee.location.name if employee.location else "Unknown"}
            Manager: {employee.manager.get_full_name() if employee.manager else "None"}
            Role: {role}
            """
            context_data.append(profile_info)

            # Leave Balance
            if hasattr(employee, "leave_balance"):
                lb = employee.leave_balance
                balance_info = f"""
                Leave Balance:
                - Casual Leave (CL): {lb.casual_leave_balance}
                - Sick Leave (SL): {lb.sick_leave_balance}
                """
                if hasattr(lb, "earned_leave_balance"):
                    balance_info += f"- Earned Leave (EL): {lb.earned_leave_balance}\n"
                context_data.append(balance_info)

            # Attendance Today
            today = timezone.now().date()
            att = Attendance.objects.filter(employee=employee, date=today).first()
            if att:
                att_info = f"Attendance Today ({today}): Status={att.status}"
                if att.clock_in:
                    att_info += f", Clock In={att.clock_in.strftime('%I:%M %p')}"
                if att.clock_out:
                    att_info += f", Clock Out={att.clock_out.strftime('%I:%M %p')}"
                context_data.append(att_info)
            else:
                context_data.append(f"Attendance Today ({today}): Not clocked in yet.")

            # Upcoming Holidays (Next 3)
            holidays = Holiday.objects.filter(company=employee.company, date__gte=today, is_active=True).order_by(
                "date"
            )[:5]
            if holidays:
                h_list = "\n".join([f"- {h.name}: {h.date.strftime('%d %b %Y')}" for h in holidays])
                context_data.append(f"Upcoming Holidays:\n{h_list}")
            else:
                context_data.append("No upcoming holidays found.")

            # Latest Payslip
            latest_payslip = Payslip.objects.filter(employee=employee).order_by("-month").first()
            if latest_payslip:
                payslip_info = (
                    f"Latest Payslip: {latest_payslip.month.strftime('%B %Y')}, Net Salary: {latest_payslip.net_salary}"
                )
                if latest_payslip.pdf_file:
                    payslip_info += f" (Download available at: {latest_payslip.pdf_file.url})"
                context_data.append(payslip_info)
            else:
                context_data.append("No payslips found.")

            # Policies & Handbook (Titles only to save tokens)
            policies = PolicySection.objects.filter(is_active=True).values_list("title", flat=True)
            handbook = HandbookSection.objects.filter(is_active=True).values_list("title", flat=True)
            if policies:
                context_data.append(f"Available Policies: {', '.join(policies)}")
            if handbook:
                context_data.append(f"Handbook Sections: {', '.join(handbook)}")

            # Team info (for Managers/Admins)
            if role in ["MANAGER", "COMPANY_ADMIN"]:
                team = Employee.objects.filter(manager=employee.user, is_active=True)
                team_count = team.count()

                # 1. Basic Stats
                present_today = Attendance.objects.filter(
                    employee__in=team, date=today, status__in=["PRESENT", "WFH"]
                ).count()

                pending_leaves = LeaveRequest.objects.filter(employee__manager=employee.user, status="PENDING").count()

                context_data.append(
                    f"Team Stats: {team_count} employees. Present Today: {present_today}. Pending Leave Requests: {pending_leaves}."
                )

                if pending_leaves > 0:
                    context_data.append(
                        "You have pending leave requests to approve. Ask user if they want to see them."
                    )

                # 2. Deep Insights (Triggered only if query asks for analytics/insights/performance/risk)
                if any(
                    w in question.lower()
                    for w in ["insight", "performance", "risk", "analytics", "attendance", "trend"]
                ):
                    # A. Attrition Risk Analysis
                    high_risk_employees = AttritionRisk.objects.filter(
                        employee__in=team, risk_level__in=["HIGH", "CRITICAL"]
                    )
                    risk_count = high_risk_employees.count()
                    context_data.append(f"Attrition Risk Analysis: {risk_count} employees are at High/Critical risk.")
                    if risk_count > 0:
                        names = ", ".join([r.employee.user.get_full_name() for r in high_risk_employees])
                        context_data.append(
                            f"High Risk Employees: {names}. (Review factors like frequent leave or late arrivals)."
                        )
                    else:
                        context_data.append("Attrition Risk Analysis: The team is stable with low predicted attrition.")

                    # B. Attendance Intelligence (Last 30 Days)
                    last_30_days = today - timedelta(days=30)
                    team_attendance = Attendance.objects.filter(employee__in=team, date__gte=last_30_days)

                    # Avg Late Arrivals
                    total_late = team_attendance.filter(is_late=True).count()
                    avg_late_per_emp = round(total_late / team_count, 1) if team_count > 0 else 0

                    context_data.append(
                        f"Attendance Intelligence (Last 30 Days): Total Late Arrivals: {total_late} (Avg {avg_late_per_emp} per employee)."
                    )

                    # Most Punctual & Least Punctual (Proxy for Performance)
                    late_counts = (
                        team_attendance.filter(is_late=True)
                        .values("employee__user__first_name")
                        .annotate(count=Count("id"))
                        .order_by("-count")
                    )
                    if late_counts:
                        most_late = f"{late_counts[0]['employee__user__first_name']} ({late_counts[0]['count']} times)"
                        context_data.append(
                            f"Performance Insight (Punctuality): Employee with most late arrivals: {most_late}."
                        )

                    # C. Performance Insights (Work Hours Proxy)
                    # We can roughly estimate 'Effort' by average work hours if clock_out exists
                    # This is a simplified logic for the chatbot context
                    context_data.append(
                        "Performance Insights: Based on system data, 'Performance' here refers to punctuality and schedule adherence."
                    )

            # System Prompt
            system_prompt = f"""
            You are an intelligent, friendly HR Assistant for {employee.company.name}.
            Your goal is to answer queries using the CONTEXT DATA provided below.

            CONTEXT DATA:
            {"".join(context_data)}

            GUIDELINES:
            1. **Answer directly based on context.**
            2. **Deep Insights:** If asked about "Team Insights", "Performance", or "Risk", separate your answer into three clear sections:
               - 📊 **Attrition Risk**
               - ⏱️ **Attendance Intelligence**
               - 🚀 **Performance Insights** (Focus on Punctuality/Consistency)
            3. **Be honest.** If data is missing (e.g. no high risk employees), say "No high risk detected".
            4. **Action Items:**
                - For detailed analysis, suggest visiting the **AI Analytics Dashboard**.
                - If the user implies **Applied Leave**, **Clock In/Out**, give the buttons.
            """

            # Call OpenAI
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": question}],
                temperature=0.7,
                max_tokens=400,
            )

            ai_text = response.choices[0].message.content.strip()

            # Add Action Buttons dynamically based on AI response keywords
            action = None
            if "apply leave" in ai_text.lower() or "leave application" in ai_text.lower():
                action = {
                    "type": "quick_replies",
                    "options": [
                        {"label": "Sick Leave", "value": "apply sick leave"},
                        {"label": "Casual Leave", "value": "apply casual leave"},
                    ],
                }
            elif "clock in" in ai_text.lower():
                action = {"type": "quick_replies", "options": [{"label": "Clock In", "value": "clock in"}]}

            # Action Items (Buttons) handling (Already handled by AI prompt + logic above)

            return {"answer": ai_text, "type": "ai_response", "action": action}

        except Exception as e:
            import traceback

            print(f"AI Error: {e}")
            print(traceback.format_exc())
            # Fallback to rule-based if AI fails
            return HRChatbot._get_fallback_response(employee.user.first_name, role)

    @staticmethod
    def _handle_approval_action(query, employee, user_name):
        """
        Handle Approve/Reject logic specifically
        """
        try:
            # Extract ID from query like "approve leave 105"
            match = re.search(r"\d+", query)
            if not match:
                return {"answer": "I couldn't identify the request ID. Please try again.", "type": "error"}

            req_id = match.group()
            leave_req = LeaveRequest.objects.get(id=req_id)

            # Action
            action = "APPROVED" if "approve" in query else "REJECTED"

            # Authorization Check
            is_authorized = False
            if (
                hasattr(employee.user, "role")
                and (employee.user.role == "COMPANY_ADMIN" or employee.user.is_superuser)
                or leave_req.employee.manager == employee.user
            ):
                is_authorized = True

            if is_authorized:
                leave_req.status = action
                leave_req.save()

                # Notify User (Mock - in real app would trigger notification)
                return {
                    "answer": f"Done! {leave_req.employee.user.first_name}'s {leave_req.leave_type} request has been **{action}**. ✅",
                    "type": "success",
                }
            else:
                return {"answer": f"⚠️ You are not authorized to {action.lower()} this request.", "type": "error"}

        except LeaveRequest.DoesNotExist:
            return {"answer": "Request not found or already deleted.", "type": "error"}
        except Exception as e:
            return {"answer": f"Error: {str(e)}", "type": "error"}

    @staticmethod
    def _handle_configuration_action(query, employee, user_name):
        """
        Handle Configuration Actions (Add Holiday, Announcement, etc.)
        """
        try:
            import re
            from datetime import datetime

            from companies.models import Holiday, Location

            # 1. Add Holiday Logic
            if "add holiday" in query:
                # Expected format: "add holiday [Name] on [Date]" e.g., "add holiday Diwali on 2024-11-01"
                # Regex to extract name and date
                # Support YYYY-MM-DD or DD-MM-YYYY
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})|(\d{2}-\d{2}-\d{4})", query)

                if not date_match:
                    return {
                        "answer": "To add a holiday, please specify the date. Format: `Add holiday [Name] on YYYY-MM-DD`.",
                        "type": "error",
                    }

                date_str = date_match.group(0)
                # Remove "add holiday", remove date, remove "on" to get name
                name_part = query.replace("add holiday", "").replace(date_str, "").replace(" on ", " ").strip()

                if not name_part:
                    return {
                        "answer": "Please specify the holiday name. Format: `Add holiday [Name] on YYYY-MM-DD`.",
                        "type": "error",
                    }

                # Parse date
                try:
                    if "-" in date_str and len(date_str.split("-")[0]) == 4:
                        holiday_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    else:
                        holiday_date = datetime.strptime(date_str, "%d-%m-%Y").date()
                except ValueError:
                    return {"answer": "Invalid date format. Please use YYYY-MM-DD (e.g., 2026-12-25).", "type": "error"}

                # Create Holiday
                # Default to employee's location if not specified (simplification)
                location = employee.location
                if not location:
                    location = Location.objects.filter(company=employee.company).first()
                if not location:
                    return {"answer": "Error: configured location not found for company.", "type": "error"}

                Holiday.objects.create(
                    company=employee.company,
                    location=location,
                    name=name_part.title(),
                    date=holiday_date,
                    holiday_type="MANDATORY",  # Default
                    created_by=user_name,
                )

                return {
                    "answer": f"✅ Success! **{name_part.title()}** has been added as a holiday on **{holiday_date.strftime('%d %b %Y')}** for {location.name}.",
                    "type": "success",
                }

            return None

        except Exception as e:
            return {"answer": f"Configuration Error: {str(e)}", "type": "error"}

    @staticmethod
    def _get_greeting_response(user_name, role):
        """Friendly greeting based on time of day"""
        hour = datetime.now().hour

        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        return {
            "answer": f"{greeting}, {user_name}! 👋\n\nHow can I help you today?",
            "type": "greeting",
        }

    # ==========================
    # Role-Specific Handlers
    # ==========================

    @staticmethod
    def _handle_admin_query(query, employee, user_name, request=None):
        """Handle Admin-specific intents with friendly tone"""

        # Employee Management
        if "employee" in query and any(w in query for w in ["add", "create", "new", "onboard", "hire"]):
            return {
                "answer": f"Sure thing, {user_name}! 😊\n\nTo add a new employee:\n1. Go to **Employees** in the sidebar\n2. Click **Add Employee**\n3. Fill in their basic details\n\nNeed help with any specific step?",
                "type": "navigation",
            }

        # Total Employees / Company Members Stats
        # Catch: "total employees", "list members", "check members", "show workforce"
        if (
            "total" in query
            or "list" in query
            or "check" in query
            or "view" in query
            or "show" in query
            or "count" in query
            or "who" in query
        ) and (
            "employee" in query
            or "staff" in query
            or "workforce" in query
            or "member" in query
            or "memebr" in query
            or "people" in query
            or "person" in query
        ):
            count = Employee.objects.filter(company=employee.company, is_active=True).count()
            dept_counts = (
                Employee.objects.filter(company=employee.company, is_active=True)
                .values("department")
                .annotate(count=Count("id"))
            )

            dept_text = "\n".join([f"• {d['department'] or 'Unassigned'}: **{d['count']}**" for d in dept_counts])

            return {
                "answer": f"Here is the company member breakdown, {user_name}: 👥\n\n**Total Members: {count}**\n\n**Department-wise:**\n{dept_text}\n\nYou can view the full detailed list in the **Employees** directory.",
                "type": "stats",
            }

        # Configuration - Specific Handlers (Prevent Loop)
        # Shift Settings
        if "shift" in query and any(
            w in query for w in ["setting", "config", "setup", "manage", "create", "edit", "update", "working"]
        ):
            return {
                "answer": f"Sure, {user_name}! ⏰\n\nTo configure Shift Settings:\n\n1. Go to **Configuration** in the sidebar\n2. Select **Shift Settings**\n3. Create or Edit shifts as needed.\n\n[Open Shift Settings](/config/shifts/)",
                "type": "navigation",
            }

        # Week-Off Settings
        if ("week" in query and "off" in query) or ("weekoff" in query):
            return {
                "answer": f"No problem, {user_name}! 📅\n\nTo configure Week-Offs:\n\n1. Go to **Configuration** in the sidebar\n2. Select **Week-Off Config**\n3. Set weekends and off days.\n\n[Open Week-Off Config](/companies/week-off-config/)",
                "type": "navigation",
            }

        # Roles & Permissions
        if "role" in query or "permission" in query or "access" in query:
            return {
                "answer": f"Got it, {user_name}! 🔐\n\nTo manage Roles & Permissions:\n\n1. Go to **Configuration** in the sidebar\n2. Select **Roles & Permissions**\n3. Define roles and access levels.\n\n[Open Roles Configuration](/companies/role-configuration/)",
                "type": "navigation",
            }

        # Holidays
        if "holiday" in query and any(w in query for w in ["config", "setting", "manage", "view", "add", "list"]):
            return {
                "answer": "Managing Holidays? 🎉\n\nYou can:\n\n1. **Add a holiday directly here:**\n   Type: `Add holiday [Name] on YYYY-MM-DD`\n   (e.g., `Add holiday New Year on 2026-01-01`)\n\n2. **Go to Configuration:**\n   Sidebar → **Configuration** → **Holidays**\n   [Open Holidays](/config/holidays/)",
                "type": "navigation",
            }

        # Configuration - API Check
        if "api" in query or "integration" in query or "token" in query:
            return {
                "answer": f"Tech savvy, {user_name}! 🤖\n\nYou can manage API tokens and integrations in:\n\n**Configuration** → **API Settings**",
                "type": "navigation",
            }

        # Configuration - General Fallback
        if any(w in query for w in ["config", "setting", "setup", "configure"]):
            return {
                "answer": f"Got it, {user_name}! 👍\n\nYou can configure settings from the **Configuration** menu:\n\n• Shift Settings\n• Week-Off Config\n• Holidays\n• Roles & Permissions\n\nWhich one would you like to set up?",
                "type": "navigation",
            }

        # Exit Actions
        if "exit" in query or "resign" in query or "terminate" in query:
            return {
                "answer": f"Managing exits, {user_name}? 🚪\n\nYou can handle resignations and terminations in:\n\n**Employees** → **Exit Management**\n\nNeed to see the attrition risk analysis?",
                "type": "navigation",
            }

        # Alerts / Anomalies
        if "alert" in query or "risk" in query or "missing" in query:
            # Missing Clock-outs
            missing_out = (
                Attendance.objects.filter(
                    employee__company=employee.company,
                    date=timezone.now().date(),
                    clock_in__isnull=False,
                    clock_out__isnull=True,
                )
                .exclude(employee=employee)
                .count()
            )

            # High Attrition Risk
            high_risk = AttritionRisk.objects.filter(
                employee__company=employee.company, risk_level__in=["HIGH", "CRITICAL"]
            ).count()

            return {
                "answer": f"Here are today's alerts, {user_name}: 🚨\n\n**Attendance:**\n• Missing Clock-outs: **{missing_out}**\n\n**Attrition Risk:**\n• High/Critical Risk Employees: **{high_risk}**\n\nCheck the **AI Features** dashboard for details.",
                "type": "alerts",
            }

        # Reports - Specific Handlers (Prevent Loop)
        if "attendance" in query and ("report" in query or "analytics" in query or "sheet" in query):
            # Quick Summary
            today = timezone.now().date()
            total_staff = Employee.objects.filter(company=employee.company, is_active=True).count()
            present = Attendance.objects.filter(
                employee__company=employee.company, date=today, clock_in__isnull=False
            ).count()

            return {
                "answer": f"Here is the Attendance Report snapshot, {user_name}: 📊\n\n**Date:** {today.strftime('%d %b %Y')}\n**Present:** {present}/{total_staff}\n\nFor detailed logs and export options, visit the full report:\n[Open Attendance Report](/analytics/report/)",
                "type": "navigation",
            }

        if "leave" in query and ("report" in query or "history" in query):
            # Quick Summary
            today = timezone.now().date()
            on_leave = LeaveRequest.objects.filter(
                employee__company=employee.company, start_date__lte=today, end_date__gte=today, status="APPROVED"
            ).count()

            return {
                "answer": f"Here is the Leave Report snapshot, {user_name}: 🌴\n\n**Employees on Leave Today:** {on_leave}\n\nFor detailed history and export:\n[Open Leave Requests](/leaves/history/)",
                "type": "navigation",
            }

        if "payroll" in query and ("report" in query or "salary" in query):
            return {
                "answer": f"Accessing Payroll Reports, {user_name}! 💰\n\nYou can view salary sheets and payroll data here:\n\n[Open Payroll Dashboard](/payroll/)",
                "type": "navigation",
            }

        if "employee" in query and ("data" in query or "list" in query or "report" in query):
            return {
                "answer": f"Managing Employee Data, {user_name}? 👥\n\nYou can view and export employee lists from the directory:\n\n[Open Employee Directory](/)",
                "type": "navigation",
            }

        # Reports - General Fallback
        if "report" in query or "export" in query:
            return {
                "answer": f"No problem, {user_name}! 📊\n\nYou can generate reports from the **Reports** section:\n\n• Attendance Reports\n• Leave Reports\n• Payroll Reports\n• Employee Data\n\nWhich report do you need?",
                "type": "navigation",
            }

        return None

    @staticmethod
    def _handle_manager_query(query, employee, user_name, request=None):
        """Handle Manager-specific intents with friendly tone"""
        from django.utils import timezone

        from employees.models import Attendance, Employee, LeaveRequest

        # Total Employees (Manager View)
        if "total" in query and ("employee" in query or "staff" in query or "workforce" in query):
            # Managers might ask this. Show team count.
            if hasattr(employee.user, "role") and (employee.user.role == "COMPANY_ADMIN" or employee.user.is_superuser):
                return HRChatbot._handle_admin_query(query, employee, user_name, request)

            team_count = Employee.objects.filter(
                company=employee.company, manager=employee.user, is_active=True
            ).count()
            return {
                "answer": f"Hi {user_name}! 👥\n\nYou have **{team_count}** employees in your team.\n\nNeed detailed attendance?",
                "type": "stats",
            }

        # Team Attendance
        if "team" in query and any(w in query for w in ["attendance", "present", "absent", "status"]):
            try:
                # If superuser or company admin, show all company employees
                if hasattr(employee.user, "role") and (
                    employee.user.role == "COMPANY_ADMIN" or employee.user.is_superuser
                ):
                    team_members = Employee.objects.filter(company=employee.company, is_active=True)
                    context_label = "Company"
                else:
                    # For regular managers, show only subordinates
                    team_members = Employee.objects.filter(
                        company=employee.company, manager=employee.user, is_active=True
                    )
                    context_label = "Team"

                present_count = Attendance.objects.filter(
                    employee__in=team_members,
                    date=timezone.now().date(),
                    clock_in__isnull=False,
                ).count()

                return {
                    "answer": f"Sure, {user_name}! 😊\n\nHere's the {context_label} status for today:\n\n👥 Total members: **{team_members.count()}**\n✅ Present today: **{present_count}**\n\nCheck the **{context_label}** section for detailed analytics.",
                    "type": "team_attendance",
                }
            except Exception as e:
                import traceback

                traceback.print_exc()
                return {
                    "answer": f"I encountered an error fetching team attendance: {str(e)}",
                    "type": "error",
                }

        # Who is absent
        if "absent" in query or "who is not here" in query:
            try:
                # Team context logic (same as above)
                if hasattr(employee.user, "role") and (
                    employee.user.role == "COMPANY_ADMIN" or employee.user.is_superuser
                ):
                    team_members = Employee.objects.filter(company=employee.company, is_active=True)
                else:
                    team_members = Employee.objects.filter(
                        company=employee.company, manager=employee.user, is_active=True
                    )

                today = timezone.now().date()
                present_ids = Attendance.objects.filter(
                    employee__in=team_members, date=today, clock_in__isnull=False
                ).values_list("employee_id", flat=True)

                absent_employees = team_members.exclude(id__in=present_ids)
                absent_names = [e.user.get_full_name() for e in absent_employees]

                if absent_names:
                    count = len(absent_names)
                    names_str = "\n".join([f"• {name}" for name in absent_names[:10]])  # Limit to 10
                    more_str = f"\n...and {count - 10} more" if count > 10 else ""

                    return {
                        "answer": f"Here is the absentee list for today ({count}): 📉\n\n{names_str}{more_str}",
                        "type": "team_attendance",
                    }
                else:
                    return {
                        "answer": "Everyone is present today! 🎉",
                        "type": "team_attendance",
                    }
            except Exception as e:
                import traceback

                traceback.print_exc()
                return {
                    "answer": f"I encountered an error fetching absentee list: {str(e)}",
                    "type": "error",
                }

        # Late Logins
        if "late" in query:
            try:
                # Team context logic
                if hasattr(employee.user, "role") and (
                    employee.user.role == "COMPANY_ADMIN" or employee.user.is_superuser
                ):
                    team_members = Employee.objects.filter(company=employee.company, is_active=True)
                else:
                    team_members = Employee.objects.filter(
                        company=employee.company, manager=employee.user, is_active=True
                    )

                late_entries = Attendance.objects.filter(
                    employee__in=team_members, date=timezone.now().date(), is_late=True
                )

                if late_entries.exists():
                    entries_str = "\n".join(
                        [f"• {a.employee.user.get_full_name()} ({a.clock_in.strftime('%H:%M')})" for a in late_entries]
                    )
                    return {
                        "answer": f"Late logins today: ⏰\n\n{entries_str}",
                        "type": "team_attendance",
                    }
                else:
                    return {
                        "answer": "No late logins today! 🌟",
                        "type": "team_attendance",
                    }
            except Exception as e:
                print(f"Error in late logins: {e}")
                pass

        # Pending Leave Requests
        if "leave" in query and any(w in query for w in ["request", "pending", "approve", "approval"]):
            try:
                # If superuser or company admin, show all company pending leaves
                if hasattr(employee.user, "role") and (
                    employee.user.role == "COMPANY_ADMIN" or employee.user.is_superuser
                ):
                    pending_count = LeaveRequest.objects.filter(
                        employee__company=employee.company, status="PENDING"
                    ).count()
                    context_msg = "in the company"
                else:
                    pending_count = LeaveRequest.objects.filter(
                        employee__manager=employee.user, status="PENDING"
                    ).count()
                    context_msg = "waiting for your approval"

                if pending_count > 0:
                    # Get top 3 pending requests for Quick Actions
                    if hasattr(employee.user, "role") and (
                        employee.user.role == "COMPANY_ADMIN" or employee.user.is_superuser
                    ):
                        pending_requests = LeaveRequest.objects.filter(
                            employee__company=employee.company, status="PENDING"
                        )[:3]
                    else:
                        pending_requests = LeaveRequest.objects.filter(
                            employee__manager=employee.user, status="PENDING"
                        )[:3]

                    request_list = []
                    quick_replies = []

                    for req in pending_requests:
                        request_list.append(
                            f"• **{req.employee.user.get_full_name()}**: {req.leave_type} ({req.start_date.strftime('%d %b')} - {req.end_date.strftime('%d %b')})"
                        )
                        quick_replies.append(
                            {
                                "label": f"Approve {req.employee.user.first_name}",
                                "value": f"approve leave {req.id}",
                            }
                        )
                        quick_replies.append(
                            {
                                "label": f"Reject {req.employee.user.first_name}",
                                "value": f"reject leave {req.id}",
                            }
                        )

                    req_str = "\n".join(request_list)

                    return {
                        "answer": f"Hi {user_name}! 📝\n\nYou have **{pending_count}** pending leave request{'s' if pending_count > 1 else ''} {context_msg}.\n\n{req_str}\n\nReview them here or use the buttons below:",
                        "type": "notification",
                        "action": {"type": "quick_replies", "options": quick_replies},
                    }
                else:
                    return {
                        "answer": f"Good news, {user_name}! 😊\n\nYou have no pending leave requests at the moment.",
                        "type": "info",
                    }
            except Exception as e:
                import traceback

                traceback.print_exc()
                return {
                    "answer": f"I encountered an error fetching leave requests: {str(e)}",
                    "type": "error",
                }

        # Handle Approval/Rejection Action
        if "approve leave" in query or "reject leave" in query:
            try:
                action = "APPROVED" if "approve" in query else "REJECTED"
                # Extract ID
                match = re.search(r"\d+", query)
                if match:
                    req_id = match.group()
                    leave_req = LeaveRequest.objects.get(id=req_id)

                    # Verify permission (Manager or Admin)
                    is_authorized = False
                    if (
                        employee.user.role == "COMPANY_ADMIN" or employee.user.is_superuser
                    ) or leave_req.employee.manager == employee.user:
                        is_authorized = True

                    if is_authorized:
                        leave_req.status = action
                        if action == "APPROVED":
                            # Update balance if needed (Usually handled in save method or signals, but let's assume standard flow)
                            pass
                        leave_req.save()

                        return {
                            "answer": f"Done! {leave_req.employee.user.first_name}'s {leave_req.leave_type} request has been **{action}**. ✅",
                            "type": "success",
                        }
                    else:
                        return {
                            "answer": f"You don't have permission to {action.lower()} this request. 🚫",
                            "type": "error",
                        }
            except LeaveRequest.DoesNotExist:
                return {
                    "answer": "I couldn't find that leave request. It might have been deleted. 🤷",
                    "type": "error",
                }
            except Exception as e:
                print(f"Error processing leave action: {e}")
                return {
                    "answer": "Something went wrong processing that request. 😔",
                    "type": "error",
                }

        # Team Performance / AI
        # Team Performance / AI Insights
        if any(w in query for w in ["performance", "insight", "analytics", "risk"]):
            try:
                # Team context logic
                if hasattr(employee.user, "role") and (
                    employee.user.role == "COMPANY_ADMIN" or employee.user.is_superuser
                ):
                    team_members = Employee.objects.filter(company=employee.company, is_active=True)
                else:
                    team_members = Employee.objects.filter(
                        company=employee.company, manager=employee.user, is_active=True
                    )

                # Fetch Attrition Risk Stats
                risk_count = AttritionRisk.objects.filter(
                    employee__in=team_members, risk_level__in=["HIGH", "CRITICAL"]
                ).count()

                risk_msg = (
                    f"• ⚠️ High Attrition Risk: **{risk_count}** employees"
                    if risk_count > 0
                    else "• ✅ Attrition Risk: **Low** (Team is stable)"
                )

                return {
                    "answer": f"Here are the insights for your team, {user_name}: 📊\n\n{risk_msg}\n\nFor meaningful details, visit the **AI Features** menu:\n\n[Open Performance Insights](/ai/performance/)\n[Open Attrition Dashboard](/ai/attrition/)",
                    "type": "navigation",
                }
            except Exception as e:
                import traceback

                traceback.print_exc()
                return {
                    "answer": f"I encountered an error fetching insights: {str(e)}",
                    "type": "error",
                }

        return None

    @staticmethod
    def _handle_employee_query(query, employee, user_name, request=None):
        """Handle standard Employee intents with friendly, conversational tone and actionable features"""

        # Check if user is actually a manager (has subordinates) but role might be EMPLOYEE
        # This acts as a safety net for "Team" queries
        # Keywords expanded to catch "pending leave", "who is absent", "total employees" etc.
        manager_keywords = [
            "team",
            "subordinate",
            "approval",
            "approve",
            "reject",
            "who is",
            "pending",
            "insight",
            "analytics",
            "risk",
            "late",
            "absent",
            "total employee",
            "total staff",
        ]

        if any(w in query for w in manager_keywords):
            # Check if they have subordinates OR are marked as Manager/Admin
            if (
                employee.user.subordinates_user.exists()
                or employee.user.role in ["MANAGER", "COMPANY_ADMIN"]
                or employee.user.is_superuser
            ):
                response = HRChatbot._handle_manager_query(query, employee, user_name, request)
                if response:
                    return response

        # Also check "Show pending leave requests" specifically if missed above
        if "leave" in query and ("request" in query or "pending" in query) and "apply" not in query:
            if employee.user.subordinates_user.exists() or employee.user.role in [
                "MANAGER",
                "COMPANY_ADMIN",
            ]:
                response = HRChatbot._handle_manager_query(query, employee, user_name, request)
                if response:
                    return response

        # Clock In/Out Actions
        if any(w in query for w in ["clock in", "clock-in", "clockin", "punch in", "check in"]):
            return HRChatbot._handle_clock_in(employee, user_name)

        if any(w in query for w in ["clock out", "clock-out", "clockout", "punch out", "check out"]):
            return HRChatbot._handle_clock_out(employee, user_name)

        # Leave Application Actions
        if any(
            phrase in query
            for phrase in [
                "apply sick leave",
                "take sick leave",
                "sick leave",
                "apply sl",
            ]
        ):
            return HRChatbot._handle_leave_application(employee, user_name, "SL")

        if any(
            phrase in query
            for phrase in [
                "apply casual leave",
                "take casual leave",
                "casual leave",
                "apply cl",
            ]
        ):
            return HRChatbot._handle_leave_application(employee, user_name, "CL")

        if any(
            phrase in query
            for phrase in [
                "apply earned leave",
                "take earned leave",
                "earned leave",
                "apply el",
            ]
        ):
            return HRChatbot._handle_leave_application(employee, user_name, "EL")

        # Regularization Action
        if any(
            phrase in query
            for phrase in [
                "regularize attendance",
                "regularization",
                "regularize",
                "missed punch",
            ]
        ):
            return HRChatbot._handle_regularization(employee, user_name)

        # Policy queries - Enhanced with actual policy data
        if any(w in query for w in ["policy", "policies", "rule", "rules", "guideline", "guidelines"]):
            return HRChatbot._get_policy_info(employee, user_name, query)

        # Employee Handbook
        if any(w in query for w in ["handbook", "employee handbook", "manual", "guide book"]):
            return HRChatbot._get_handbook_info(employee, user_name, query)

        # Leave Balance - check before general "leave" queries
        if any(
            w in query
            for w in [
                "leave balance",
                "leaves left",
                "remaining leave",
                "how many leave",
                "leave quota",
                "check leave",
            ]
        ):
            return HRChatbot._get_leave_balance_response(employee, user_name)

        # Leave Application (general)
        if any(
            phrase in query
            for phrase in [
                "apply leave",
                "apply for leave",
                "request leave",
                "take leave",
                "book leave",
            ]
        ):
            return {
                "answer": f"Sure, {user_name}! 📝\n\nWhich type of leave would you like to apply?\n\n🏥 **Sick Leave (SL)**\n🌴 **Casual Leave (CL)**\n✈️ **Earned Leave (EL)**\n\nJust tell me which one, and I'll help you apply!\n\nOr you can go to:\n**Leaves** → **Apply Leave**",
                "type": "leave_options",
                "action": {
                    "type": "quick_replies",
                    "options": [
                        {"label": "Sick Leave", "value": "apply sick leave"},
                        {"label": "Casual Leave", "value": "apply casual leave"},
                        {"label": "Earned Leave", "value": "apply earned leave"},
                    ],
                },
            }

        # Portal Access / Login / Account
        if any(
            w in query
            for w in [
                "portal",
                "login",
                "access",
                "account",
                "username",
                "password",
                "credentials",
            ]
        ):
            return HRChatbot._get_portal_access_info(employee, user_name, query)

        # General leave info (only if not caught above)
        if "leave" in query and not any(w in query for w in ["balance", "apply", "request"]):
            return HRChatbot._get_leave_balance_response(employee, user_name)

        # Attendance Status (Today)
        if any(
            w in query
            for w in [
                "attendance",
                "present",
                "check my attendance",
                "attendance status",
                "today attendance",
            ]
        ):
            return HRChatbot._get_attendance_info(employee, user_name)

        # Holidays
        if any(w in query for w in ["holiday", "holidays", "festival", "off day", "upcoming holiday"]):
            return HRChatbot._get_holiday_info(employee, user_name)

        # Payroll / Salary
        if any(w in query for w in ["salary", "payslip", "pay", "payroll", "income", "ctc"]):
            if "download" in query or "view" in query or "see" in query:
                return {
                    "answer": f"Sure, {user_name}! 💰\n\nTo download your payslip:\n\n**Step 1:** Click **'Me'** in the sidebar\n**Step 2:** Select **'Finance'**\n**Step 3:** Choose the month\n**Step 4:** Click **'Download Payslip'**\n\nNeed help with anything else?",
                    "type": "navigation",
                }
            else:
                return {
                    "answer": f"Sure, {user_name}! 💰\n\nYou can view your salary details and download payslips from:\n\n**Me** → **Finance**\n\nNeed help finding it?",
                    "type": "navigation",
                }

        # Profile
        if "profile" in query or "personal detail" in query or "update detail" in query:
            if "update" in query or "edit" in query or "change" in query:
                return {
                    "answer": f"No problem, {user_name}! 👤\n\nTo update your profile:\n\n**Step 1:** Go to **'Me'** → **'My Profile'**\n**Step 2:** Click **'Edit Profile'**\n**Step 3:** Update the information\n**Step 4:** Click **'Save Changes'**\n\nWhat would you like to update?",
                    "type": "navigation",
                }
            else:
                return {
                    "answer": f"No problem, {user_name}! 👤\n\nYou can view and update your profile in:\n\n**Me** → **My Profile**\n\nWhat would you like to update?",
                    "type": "navigation",
                }

        # Shift Info
        if "shift" in query or "timing" in query or "schedule" in query or "work time" in query:
            return HRChatbot._get_shift_info(employee, user_name)

        # Manager Info
        if "manager" in query or "reporting" in query or "supervisor" in query or "boss" in query:
            return HRChatbot._get_manager_info(employee, user_name)

        return None

    # ==========================
    # Detailed Response Implementations
    # ==========================

    @staticmethod
    def _get_leave_balance_response(employee, user_name):
        """Friendly leave balance response"""
        try:
            # Safe access to leave balance
            if not hasattr(employee, "leave_balance"):
                return {
                    "answer": f"Hi {user_name}, it seems your leave balance account hasn't been set up yet. Please contact HR.",
                    "type": "error",
                }

            balance = employee.leave_balance
            total = balance.total_balance

            # Core leave types that definitely exist
            response_parts = [
                f"Sure, {user_name}! 😊\n\nHere's your leave balance:\n",
                f"🌴 Casual Leave: **{balance.casual_leave_balance:.1f}** days",
                f"🏥 Sick Leave: **{balance.sick_leave_balance:.1f}** days",
            ]

            # Optional leave types - check existence first
            if hasattr(balance, "earned_leave_balance"):
                response_parts.append(f"✈️ Earned Leave: **{balance.earned_leave_balance:.1f}** days")

            if hasattr(balance, "comp_off_balance"):
                response_parts.append(f"⭐ Comp Off: **{balance.comp_off_balance:.1f}** days")

            response_parts.append(f"\n📊 **Total Available: {total:.1f} days**\n")
            response_parts.append("Need to apply for leave?")

            return {
                "answer": "\n".join(response_parts),
                "type": "leave_balance",
            }
        except Exception as e:
            import traceback

            print(f"Chatbot Balance Error: {str(e)}")
            print(traceback.format_exc())
            return {
                "answer": f"Sorry {user_name}, I couldn't fetch your leave balance right now. 😔\n\nPlease check the **Leave** section or contact HR.",
                "type": "error",
            }

    @staticmethod
    def _get_shift_info(employee, user_name):
        """Friendly shift information response"""
        shift = getattr(employee, "assigned_shift", None)

        # Handle legacy shift_schedule (string) lookup
        if not shift and hasattr(employee, "shift_schedule") and employee.shift_schedule:
            # Try to find the shift object by name
            from companies.models import ShiftSchedule

            shift = ShiftSchedule.objects.filter(company=employee.company, name__iexact=employee.shift_schedule).first()

        if shift:
            return {
                "answer": f"Got it, {user_name}! ⏰\n\nHere's your shift schedule:\n\n"
                f"📋 **{shift.name}**\n"
                f"🕐 Time: **{shift.start_time.strftime('%I:%M %p')} - {shift.end_time.strftime('%I:%M %p')}**\n"
                f"📅 Working Days: {', '.join(shift.working_days_list)}\n\n"
                f"Need to change your shift?",
                "type": "shift_info",
            }
        else:
            return {
                "answer": f"Sorry {user_name}, your shift isn't configured yet. 😔\n\nPlease contact HR to set it up.",
                "type": "error",
            }

    @staticmethod
    def _get_holiday_info(employee, user_name):
        """Friendly holiday information response"""
        from companies.models import Holiday

        upcoming_holidays = Holiday.objects.filter(
            company=employee.company, date__gte=timezone.now().date(), is_active=True
        ).order_by("date")[:5]

        if upcoming_holidays:
            holiday_list = "\n".join([f"🎉 **{h.name}** - {h.date.strftime('%d %b %Y')}" for h in upcoming_holidays])
            return {
                "answer": f"Sure, {user_name}! 🎊\n\nHere are the upcoming holidays:\n\n{holiday_list}\n\nPlanning a vacation?",
                "type": "holidays",
            }
        else:
            return {
                "answer": f"Hi {user_name}! 📅\n\nNo upcoming holidays found for your location right now.\n\nCheck back later!",
                "type": "info",
            }

    @staticmethod
    def _get_manager_info(employee, user_name):
        """Friendly manager information response"""
        if employee.manager:
            return {
                "answer": f"Sure, {user_name}! 👤\n\nYour reporting manager is:\n\n"
                f"**{employee.manager.get_full_name()}**\n"
                f"📧 {employee.manager.email}\n\n"
                f"Need to contact them?",
                "type": "manager_info",
            }
        else:
            return {
                "answer": f"Hi {user_name}! 😊\n\nYou don't have a reporting manager assigned yet.\n\nContact HR if this seems wrong.",
                "type": "info",
            }

    @staticmethod
    def _get_attendance_info(employee, user_name):
        """Friendly attendance status response with options"""
        today = timezone.now().date()
        record = Attendance.objects.filter(employee=employee, date=today).first()

        if record:
            if record.clock_in and record.clock_out:
                # Both clock-in and clock-out done
                return {
                    "answer": f"Sure, {user_name}! 😊\n\nHere's your attendance for today:\n\n"
                    f"⏰ Clock-in: **{record.clock_in.strftime('%I:%M %p')}**\n"
                    f"⏰ Clock-out: **{record.clock_out.strftime('%I:%M %p')}**\n"
                    f"📊 Status: **{record.get_status_display()}**\n\n"
                    f"Want to view past attendance?",
                    "type": "attendance",
                }
            elif record.clock_in:
                # Only clock-in done
                return {
                    "answer": f"Sure, {user_name}! 😊\n\nHere's your attendance summary for today:\n\n"
                    f"⏰ Clock-in: **{record.clock_in.strftime('%I:%M %p')}**\n"
                    f"⏰ Clock-out: **Not yet**\n\n"
                    f"Do you want to clock out or view past attendance?",
                    "type": "attendance",
                }
            else:
                return {
                    "answer": f"Hi {user_name}! 📅\n\nYou haven't clocked in yet today.\n\nWould you like to clock in now?",
                    "type": "attendance",
                }
        else:
            return {
                "answer": f"Hi {user_name}! 📅\n\nNo attendance record found for today.\n\nWould you like to clock in?",
                "type": "attendance",
            }

    @staticmethod
    def _get_fallback_response(user_name, role):
        """Friendly fallback when query not understood"""
        common_topics = "• Leave Balance\n• Attendance\n• Holidays\n• Payslips\n• Policies"
        manager_topics = "\n• Team Attendance\n• Leave Approvals\n• Team Insights"
        admin_topics = "\n• Add Employees\n• Configuration\n• Reports"

        topics = common_topics
        if role == "MANAGER":
            topics += manager_topics
        if role == "COMPANY_ADMIN":
            topics += manager_topics + admin_topics

        return {
            "answer": f"👋 I'm here to help, {user_name}! ⭐\n\n**I can answer questions about:**\n{topics}\n\nWhat would you like to know?",
            "type": "general",
        }

    @staticmethod
    def _get_policy_info(employee, user_name, query):
        """Fetch and display policy information from database"""
        from employees.models import PolicySection

        try:
            # Get all active policy sections
            policies = PolicySection.objects.filter(is_active=True).order_by("order")

            if not policies.exists():
                return {
                    "answer": f"Hi {user_name}! 📚\n\nNo policies have been configured yet. Please contact HR for policy information.\n\n**To access policies when available:**\n**Me** → **Policies**",
                    "type": "info",
                }

            # Check if user is asking for a specific policy
            specific_keywords = {
                "leave": ["leave", "vacation", "time off", "pto"],
                "attendance": ["attendance", "clock", "punch", "timing"],
                "code of conduct": ["conduct", "behavior", "ethics", "discipline"],
                "hr": ["hr", "human resource", "recruitment", "hiring"],
                "dress": ["dress", "attire", "uniform", "clothing"],
                "work from home": ["wfh", "work from home", "remote", "hybrid"],
            }

            # Try to find specific policy
            for policy_type, keywords in specific_keywords.items():
                if any(keyword in query for keyword in keywords):
                    matching_policy = policies.filter(title__icontains=policy_type.split()[0]).first()
                    if matching_policy:
                        # Strip HTML tags for cleaner display
                        import re

                        clean_content = re.sub("<[^<]+?>", "", matching_policy.content)
                        clean_content = clean_content.strip()[:500]  # Limit length

                        return {
                            "answer": f"Sure, {user_name}! 📚\n\n**{matching_policy.title}**\n\n{clean_content}...\n\n**For complete details:**\n**Me** → **Policies** → **{matching_policy.title}**\n\nNeed information about other policies?",
                            "type": "policy_detail",
                        }

            # General policy overview
            policy_list = "\n".join([f"• {p.title}" for p in policies[:10]])

            return {
                "answer": f"Sure thing, {user_name}! 📚\n\n**Available Company Policies:**\n\n{policy_list}\n\n**To view full details:**\n**Me** → **Policies**\n\nWhich policy would you like to know more about?",
                "type": "policy_list",
            }

        except Exception:
            return {
                "answer": f"Sorry {user_name}, I encountered an error fetching policy information. 😔\n\nPlease access policies directly:\n**Me** → **Policies**\n\nOr contact HR for assistance.",
                "type": "error",
            }

    @staticmethod
    def _get_handbook_info(employee, user_name, query):
        """Fetch and display employee handbook information from database"""
        from employees.models import HandbookSection

        try:
            # Get all active handbook sections
            handbook_sections = HandbookSection.objects.filter(is_active=True).order_by("order")

            if not handbook_sections.exists():
                return {
                    "answer": f"Hi {user_name}! 📖\n\nThe employee handbook is not available yet. Please contact HR for handbook information.\n\n**To access handbook when available:**\n**Me** → **Employee Handbook**",
                    "type": "info",
                }

            # Check if user is asking for a specific section
            specific_keywords = {
                "welcome": ["welcome", "introduction", "intro", "getting started"],
                "benefits": ["benefit", "insurance", "health", "medical", "perks"],
                "compensation": ["compensation", "salary", "pay", "bonus", "increment"],
                "working hours": ["working hours", "schedule", "shift", "timing"],
                "leave": ["leave", "vacation", "pto", "time off"],
                "code of conduct": ["conduct", "behavior", "ethics"],
            }

            # Try to find specific section
            for section_type, keywords in specific_keywords.items():
                if any(keyword in query for keyword in keywords):
                    matching_section = handbook_sections.filter(title__icontains=section_type.split()[0]).first()
                    if matching_section:
                        # Strip HTML tags for cleaner display
                        import re

                        clean_content = re.sub("<[^<]+?>", "", matching_section.content)
                        clean_content = clean_content.strip()[:500]  # Limit length

                        return {
                            "answer": f"Sure, {user_name}! 📖\n\n**{matching_section.title}**\n\n{clean_content}...\n\n**For complete details:**\n**Me** → **Employee Handbook** → **{matching_section.title}**\n\nNeed information about other sections?",
                            "type": "handbook_detail",
                        }

            # General handbook overview
            section_list = "\n".join([f"• {s.title}" for s in handbook_sections[:10]])

            return {
                "answer": f"Sure thing, {user_name}! 📖\n\n**Employee Handbook Sections:**\n\n{section_list}\n\n**To view full handbook:**\n**Me** → **Employee Handbook**\n\nWhich section would you like to know more about?",
                "type": "handbook_list",
            }

        except Exception:
            return {
                "answer": f"Sorry {user_name}, I encountered an error fetching handbook information. 😔\n\nPlease access the handbook directly:\n**Me** → **Employee Handbook**\n\nOr contact HR for assistance.",
                "type": "error",
            }

    @staticmethod
    def _get_portal_access_info(employee, user_name, query):
        """Provide portal access and account information"""

        # Check what specific info they're asking about
        if "forgot" in query or "reset" in query or "password" in query:
            return {
                "answer": f"No worries, {user_name}! 🔐\n\n**To reset your password:**\n\n**Step 1:** Go to the login page\n**Step 2:** Click **'Forgot Password?'**\n**Step 3:** Enter your email address\n**Step 4:** Check your email for OTP\n**Step 5:** Enter OTP and set new password\n\n**Security Tip:** Use a strong password with letters, numbers, and symbols!\n\nNeed help with the process?",
                "type": "password_reset",
            }

        if "username" in query or "email" in query or "login" in query:
            return {
                "answer": f"Sure, {user_name}! 👤\n\n**Your Portal Access Details:**\n\n📧 **Email/Username:** {employee.user.email}\n🆔 **Employee ID:** {employee.badge_id or 'Not assigned'}\n👤 **Full Name:** {employee.user.get_full_name()}\n\n**Portal URL:** {employee.company.name} HRMS Portal\n\n**Note:** Your email is your username for login.\n\nForgot your password?",
                "type": "account_info",
            }

        # General portal access info
        return {
            "answer": f"Sure, {user_name}! 🌐\n\n**Portal Access Information:**\n\n📧 **Login Email:** {employee.user.email}\n🆔 **Employee ID:** {employee.badge_id or 'Not assigned'}\n🏢 **Company:** {employee.company.name}\n📍 **Location:** {employee.location.name if employee.location else 'Not assigned'}\n\n**What you can access:**\n• Personal Dashboard\n• Attendance & Leaves\n• Payslips & Documents\n• Company Policies\n• Team Information\n\n**Need help with:**\n• Forgot password?\n• Can't login?\n• Account issues?",
            "type": "portal_info",
        }

    # ==========================
    # Actionable Features
    # ==========================

    @staticmethod
    def _handle_clock_in(employee, user_name):
        """Handle clock-in action"""
        from django.utils import timezone

        today = timezone.now().date()
        attendance = Attendance.objects.filter(employee=employee, date=today).first()

        if attendance and attendance.clock_in:
            clock_in_time = attendance.clock_in.strftime("%I:%M %p")
            return {
                "answer": f"Hi {user_name}! 😊\n\nYou've already clocked in today at **{clock_in_time}**.\n\nHave a productive day!",
                "type": "info",
            }

        return {
            "answer": f"Sure, {user_name}! ⏰\n\nReady to clock in?\n\nClick the button below to clock in now!",
            "type": "action",
            "action": {
                "type": "button",
                "label": "🕐 Clock In Now",
                "url": "/me/home/",  # Redirect to home page where clock-in button is
                "method": "GET",
            },
        }

    @staticmethod
    def _handle_clock_out(employee, user_name):
        """Handle clock-out action"""
        from django.utils import timezone

        today = timezone.now().date()
        attendance = Attendance.objects.filter(employee=employee, date=today).first()

        if not attendance or not attendance.clock_in:
            return {
                "answer": f"Hi {user_name}! 😊\n\nYou haven't clocked in yet today.\n\nWould you like to clock in first?",
                "type": "info",
            }

        if attendance.clock_out:
            clock_out_time = attendance.clock_out.strftime("%I:%M %p")
            return {
                "answer": f"Hi {user_name}! 😊\n\nYou've already clocked out today at **{clock_out_time}**.\n\nSee you tomorrow!",
                "type": "info",
            }

        return {
            "answer": f"Sure, {user_name}! ⏰\n\nReady to clock out?\n\nClick the button below to clock out now!",
            "type": "action",
            "action": {
                "type": "button",
                "label": "🕐 Clock Out Now",
                "url": "/me/home/",  # Redirect to home page where clock-out button is
                "method": "GET",
            },
        }

    @staticmethod
    def _handle_leave_application(employee, user_name, leave_type):
        """Handle leave application action"""
        leave_names = {"SL": "Sick Leave", "CL": "Casual Leave", "EL": "Earned Leave"}

        leave_name = leave_names.get(leave_type, "Leave")

        # Check leave balance
        try:
            balance = employee.leave_balance
            if leave_type == "SL":
                available = balance.sick_leave_balance
            elif leave_type == "CL":
                available = balance.casual_leave_balance
            elif leave_type == "EL":
                available = balance.earned_leave_balance
            else:
                available = 0

            balance_text = f"\n\n📊 **Available {leave_name}:** {available:.1f} days"
        except:
            balance_text = ""

        return {
            "answer": f"Sure, {user_name}! 📝\n\nI'll help you apply for **{leave_name}**.{balance_text}\n\nClick the button below to fill in the details:",
            "type": "action",
            "action": {
                "type": "button",
                "label": f"📝 Apply {leave_name}",
                "url": "/leaves/apply/",  # Redirect to leave application page
                "method": "GET",
                "data": {"leave_type": leave_type},
            },
        }

    @staticmethod
    def _handle_regularization(employee, user_name):
        """Handle regularization request action"""
        return {
            "answer": f"Sure, {user_name}! 📝\n\nI'll help you regularize your attendance.\n\nClick the button below to submit a regularization request:",
            "type": "action",
            "action": {
                "type": "button",
                "label": "📝 Regularize Attendance",
                "url": "/attendance/regularize/",  # Redirect to regularization page
                "method": "GET",
            },
        }


class ResumeParser:
    """
    Parse resume PDFs and extract key information
    """

    @staticmethod
    def parse_resume(file_path):
        """
        Extract information from resume file
        """
        try:
            # Try to extract text from PDF
            text = ResumeParser._extract_text_from_pdf(file_path)

            # Extract information using regex patterns
            parsed_data = {
                "name": ResumeParser._extract_name(text),
                "email": ResumeParser._extract_email(text),
                "phone": ResumeParser._extract_phone(text),
                "skills": ResumeParser._extract_skills(text),
            }

            return parsed_data
        except Exception as e:
            return {
                "error": str(e),
                "name": None,
                "email": None,
                "phone": None,
                "skills": None,
            }

    @staticmethod
    def _extract_text_from_pdf(file_path):
        """
        Extract text from PDF file
        """
        try:
            import PyPDF2

            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
        except ImportError:
            # Fallback: return empty string if PyPDF2 not installed
            return ""
        except Exception:
            return ""

    @staticmethod
    def _extract_email(text):
        """Extract email address from text"""
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    @staticmethod
    def _extract_phone(text):
        """Extract phone number from text"""
        # Indian phone number patterns
        phone_patterns = [
            r"\+91[-\s]?\d{10}",
            r"\d{10}",
            r"\(\d{3}\)[-\s]?\d{3}[-\s]?\d{4}",
        ]

        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None

    @staticmethod
    def _extract_name(text):
        """Extract name from text (first line usually)"""
        lines = text.split("\n")

        # Try to find name in first 10 lines
        for line in lines[:10]:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip lines that are too short or too long
            if len(line) < 3 or len(line) > 60:
                continue

            # Skip lines with common resume keywords
            skip_keywords = [
                "resume",
                "cv",
                "curriculum",
                "vitae",
                "profile",
                "summary",
                "objective",
                "experience",
                "education",
                "skills",
                "contact",
                "email",
                "phone",
                "address",
                "linkedin",
                "github",
                "@",
            ]
            if any(keyword in line.lower() for keyword in skip_keywords):
                continue

            # Check if line looks like a name (mostly letters with possible dots/commas)
            # Allow letters, spaces, dots, commas, apostrophes
            if re.match(r"^[A-Za-z\s\.\,\']+$", line):
                # Count words - names usually have 2-4 words
                words = line.split()
                if 1 <= len(words) <= 4:
                    # Check if words are capitalized (typical for names)
                    if all(word[0].isupper() for word in words if word):
                        return line

            # Fallback: if line has 2-3 capitalized words, likely a name
            words = line.split()
            if 2 <= len(words) <= 3:
                if all(word[0].isupper() and word.isalpha() for word in words):
                    return line

        # Ultimate fallback: return first non-empty, non-keyword line
        for line in lines[:15]:
            line = line.strip()
            if line and len(line) > 2 and len(line) < 60:
                # Skip if it contains @ or common keywords
                if "@" not in line and not any(kw in line.lower() for kw in ["resume", "cv", "email", "phone"]):
                    return line

        return None

    @staticmethod
    def _extract_skills(text):
        """Extract skills from text"""
        # Common technical skills
        skill_keywords = [
            "Python",
            "Java",
            "JavaScript",
            "React",
            "Angular",
            "Vue",
            "Django",
            "Flask",
            "Node.js",
            "Express",
            "SQL",
            "MongoDB",
            "PostgreSQL",
            "MySQL",
            "AWS",
            "Azure",
            "Docker",
            "Kubernetes",
            "Git",
            "HTML",
            "CSS",
            "TypeScript",
            "C++",
            "C#",
            "PHP",
            "Machine Learning",
            "AI",
            "Data Science",
            "DevOps",
        ]

        found_skills = []
        text_lower = text.lower()

        for skill in skill_keywords:
            if skill.lower() in text_lower:
                found_skills.append(skill)

        return ", ".join(found_skills) if found_skills else None
