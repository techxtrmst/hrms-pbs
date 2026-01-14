from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import AttritionRisk, ResumeParsingJob, ChatMessage
from .ai_utils import AttritionPredictor, HRChatbot
from .attendance_intelligence import AttendanceIntelligence
from .leave_prediction import LeavePrediction
from .smart_notifications import SmartNotifications
from employees.models import Employee
from loguru import logger
from core.error_handling import safe_get_employee_profile, capture_exception
import json


@login_required
def ai_features_hub(request):
    """
    AI Features Hub - Shows all available AI features
    """
    is_manager = request.user.is_staff or request.user.is_superuser

    context = {"is_manager": is_manager}

    return render(request, "ai_assistant/ai_hub.html", context)


@login_required
def attrition_dashboard(request):
    """
    Display attrition risk dashboard for managers/admins
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to access this page.")
        return redirect("dashboard")

    # Get company from request
    company = request.company

    # Get all employees in the company
    employees = Employee.objects.filter(company=company, is_active=True)

    # Calculate or fetch risk scores
    risk_data = []
    for emp in employees:
        risk_obj, created = AttritionRisk.objects.get_or_create(employee=emp)

        # Recalculate if older than 7 days or newly created
        from django.utils import timezone
        from datetime import timedelta

        if created or (timezone.now() - risk_obj.last_updated) > timedelta(days=7):
            risk_result = AttritionPredictor.calculate_risk_score(emp)
            risk_obj.risk_score = risk_result["score"]
            risk_obj.risk_level = risk_result["risk_level"]
            risk_obj.risk_factors = risk_result["factors"]
            risk_obj.save()

        risk_data.append({"employee": emp, "risk": risk_obj})

    # Sort by risk score (highest first)
    risk_data.sort(key=lambda x: x["risk"].risk_score, reverse=True)

    # Calculate statistics
    total_employees = len(risk_data)
    critical_count = sum(1 for r in risk_data if r["risk"].risk_level == "CRITICAL")
    high_count = sum(1 for r in risk_data if r["risk"].risk_level == "HIGH")
    medium_count = sum(1 for r in risk_data if r["risk"].risk_level == "MEDIUM")
    low_count = sum(1 for r in risk_data if r["risk"].risk_level == "LOW")

    context = {
        "risk_data": risk_data,
        "stats": {
            "total": total_employees,
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        },
    }

    return render(request, "ai_assistant/attrition_dashboard.html", context)


@login_required
def chatbot_page(request):
    """
    Standalone chatbot page
    """
    return render(request, "ai_assistant/chatbot_page.html")


@login_required
@require_http_methods(["POST"])
def chatbot_query(request):
    """
    Handle chatbot queries via AJAX
    """
    try:
        data = json.loads(request.body)
        question = data.get("question", "")

        if not question:
            return JsonResponse({"error": "No question provided"}, status=400)

        # Get employee profile
        employee = safe_get_employee_profile(request.user)
        if not employee:
            return JsonResponse({"error": "Employee profile not found"}, status=404)

        # Determine role (simplified for standard chatbot view)
        role = "EMPLOYEE"
        if request.user.is_superuser or request.user.role == "COMPANY_ADMIN":
            role = "COMPANY_ADMIN"
        elif request.user.is_staff or request.user.role == "MANAGER":
            role = "MANAGER"

        # Get response from chatbot
        bot_response = HRChatbot.get_response(
            question, employee, role=role, request=request
        )

        # Extract answer from response
        if isinstance(bot_response, dict):
            response_text = bot_response.get("answer", str(bot_response))
            response_type = bot_response.get("type", "general")
            action_data = bot_response.get("action", None)
        else:
            response_text = str(bot_response)
            response_type = "general"
            action_data = None

        # Save chat history
        try:
            ChatMessage.objects.create(
                user=request.user, user_message=question, bot_response=response_text
            )
        except Exception as e:
            print(f"Error saving chat history: {e}")

        return JsonResponse(
            {
                "success": True,
                "response": response_text,
                "type": response_type,
                "action": action_data,
            }
        )

    except Exception as e:
        import traceback

        print(f"Chatbot error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def resume_parser_view(request):
    """
    Enhanced resume parser interface with comprehensive data extraction
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to access this page.")
        return redirect("dashboard")

    if request.method == "POST" and request.FILES.get("resume"):
        resume_file = request.FILES["resume"]

        # Save the resume
        job = ResumeParsingJob.objects.create(resume=resume_file)

        # Parse the resume using enhanced parser
        try:
            from .enhanced_resume_parser import EnhancedResumeParser

            parsed_data = EnhancedResumeParser.parse_resume(job.resume.path)

            # Check for errors
            if "error" in parsed_data and not parsed_data.get("name"):
                raise Exception(parsed_data["error"])

            # Update job with all parsed data
            # Basic Details
            job.parsed_name = parsed_data.get("name")
            job.parsed_email = parsed_data.get("email")
            job.parsed_phone = parsed_data.get("phone")
            job.parsed_location = parsed_data.get("location")
            job.parsed_linkedin = parsed_data.get("linkedin")
            job.parsed_github = parsed_data.get("github")
            job.parsed_portfolio = parsed_data.get("portfolio")

            # Skills
            job.parsed_skills = parsed_data.get("skills")  # Legacy comma-separated
            job.parsed_skills_json = parsed_data.get("skills_json")  # Categorized JSON

            # Education
            job.parsed_education = parsed_data.get("education")

            # Experience
            experience = parsed_data.get("experience", [])
            if experience:
                for exp in experience:
                    if not exp.get("end_date"):
                        exp["end_date"] = "Present"
            job.parsed_experience = experience
            job.total_experience_years = parsed_data.get("total_experience_years")

            # Projects
            job.parsed_projects = parsed_data.get("projects")

            # Certifications
            job.parsed_certifications = parsed_data.get("certifications")

            # Categorization
            job.candidate_type = parsed_data.get("candidate_type")
            job.role_fit = parsed_data.get("role_fit")
            job.domain = parsed_data.get("domain")

            # Duplicate Detection
            job.duplicate_check_hash = parsed_data.get("duplicate_check_hash")

            # Check for duplicates
            duplicate = (
                ResumeParsingJob.objects.filter(
                    duplicate_check_hash=job.duplicate_check_hash, status="PROCESSED"
                )
                .exclude(id=job.id)
                .first()
            )

            if duplicate:
                job.is_duplicate = True
                job.duplicate_of = duplicate

            # Also check by email/phone
            if job.parsed_email or job.parsed_phone:
                email_duplicate = (
                    ResumeParsingJob.objects.filter(
                        parsed_email=job.parsed_email, status="PROCESSED"
                    )
                    .exclude(id=job.id)
                    .first()
                    if job.parsed_email
                    else None
                )

                phone_duplicate = (
                    ResumeParsingJob.objects.filter(
                        parsed_phone=job.parsed_phone, status="PROCESSED"
                    )
                    .exclude(id=job.id)
                    .first()
                    if job.parsed_phone
                    else None
                )

                if email_duplicate or phone_duplicate:
                    job.is_duplicate = True
                    job.duplicate_of = email_duplicate or phone_duplicate

            job.status = "PROCESSED"
            job.save()

            messages.success(request, "Resume parsed successfully!")
            return redirect("resume_parser_result", job_id=job.id)

        except Exception as e:
            job.status = "FAILED"
            job.save()
            messages.error(request, f"Failed to parse resume: {str(e)}")

    return render(request, "ai_assistant/resume_parser.html")


@login_required
def resume_parser_result(request, job_id):
    """
    Display parsed resume results
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to access this page.")
        return redirect("dashboard")

    try:
        job = ResumeParsingJob.objects.get(id=job_id)
    except ResumeParsingJob.DoesNotExist:
        messages.error(request, "Resume parsing job not found.")
        return redirect("resume_parser")

    context = {"job": job}

    return render(request, "ai_assistant/resume_result.html", context)


@login_required
def employee_risk_detail(request, employee_id):
    """
    Show detailed risk analysis for a specific employee
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to access this page.")
        return redirect("dashboard")

    try:
        employee = Employee.objects.get(id=employee_id, company=request.company)
        risk_obj = AttritionRisk.objects.get(employee=employee)
    except (Employee.DoesNotExist, AttritionRisk.DoesNotExist):
        messages.error(request, "Employee or risk data not found.")
        return redirect("attrition_dashboard")

    context = {"employee": employee, "risk": risk_obj}

    return render(request, "ai_assistant/risk_detail.html", context)


@login_required
def attendance_intelligence_dashboard(request):
    """
    AI Attendance Intelligence Dashboard
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to access this page.")
        return redirect("dashboard")

    company = request.company

    # Get company-wide insights
    company_insights = AttendanceIntelligence.get_company_insights(company, days=30)

    context = {
        "company_insights": company_insights,
        "high_risk_employees": company_insights["high_risk_employees"][:10],  # Top 10
    }

    return render(request, "ai_assistant/attendance_intelligence.html", context)


@login_required
def employee_attendance_detail(request, employee_id):
    """
    Detailed attendance analysis for a specific employee
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to access this page.")
        return redirect("dashboard")

    try:
        employee = Employee.objects.get(id=employee_id, company=request.company)
    except Employee.DoesNotExist:
        messages.error(request, "Employee not found.")
        return redirect("attendance_intelligence")

    # Get attendance analysis
    analysis = AttendanceIntelligence.analyze_employee_patterns(employee, days=30)

    context = {"employee": employee, "analysis": analysis}

    return render(request, "ai_assistant/employee_attendance_detail.html", context)


@login_required
def leave_prediction_dashboard(request):
    """
    AI Leave Prediction Dashboard
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to access this page.")
        return redirect("dashboard")

    company = request.company

    # Get team shortage predictions
    shortage_prediction = LeavePrediction.predict_team_shortage(company, days_ahead=14)

    # Get leave patterns for high-risk employees
    employees = Employee.objects.filter(company=company, is_active=True)[:20]
    employee_patterns = []

    for emp in employees:
        patterns = LeavePrediction.analyze_leave_patterns(emp, months=6)
        if patterns["total_leaves"] > 0:
            employee_patterns.append(patterns)

    context = {
        "shortage_prediction": shortage_prediction,
        "employee_patterns": employee_patterns,
        "critical_days": shortage_prediction["critical_days"],
    }

    return render(request, "ai_assistant/leave_prediction.html", context)


@login_required
def my_leave_insights(request):
    """
    Personal leave insights for employees
    """
    employee = safe_get_employee_profile(request.user)
    if not employee:
        messages.error(request, "Employee profile not found.")
        return redirect("dashboard")

    # Get personal leave patterns
    patterns = LeavePrediction.analyze_leave_patterns(employee, months=6)

    # Get recommendations
    recommendations = LeavePrediction.get_leave_recommendations(employee)

    context = {"patterns": patterns, "recommendations": recommendations}

    return render(request, "ai_assistant/my_leave_insights.html", context)


@login_required
def smart_notifications_dashboard(request):
    """
    Smart Notifications Dashboard
    """
    employee = safe_get_employee_profile(request.user)
    if not employee:
        messages.error(request, "Employee profile not found.")
        return redirect("dashboard")

    # Get all alerts for employee
    employee_alerts = SmartNotifications.get_all_alerts_for_employee(employee)

    # Get manager alerts if user is a manager
    manager_alerts = []
    if request.user.is_staff or request.user.is_superuser:
        manager_alerts = SmartNotifications.get_all_alerts_for_manager(request.user)

    # Get daily digest
    daily_digest = SmartNotifications.generate_daily_digest(employee)

    context = {
        "employee_alerts": employee_alerts,
        "manager_alerts": manager_alerts,
        "daily_digest": daily_digest,
        "total_alerts": len(employee_alerts) + len(manager_alerts),
    }

    return render(request, "ai_assistant/smart_notifications.html", context)


@login_required
@require_http_methods(["GET"])
def get_notifications_api(request):
    """
    API endpoint to get notifications (for AJAX calls)
    """
    employee = safe_get_employee_profile(request.user)
    if not employee:
        return JsonResponse({"error": "Employee profile not found"}, status=404)

    # Get alerts
    employee_alerts = SmartNotifications.get_all_alerts_for_employee(employee)

    # Get manager alerts if applicable
    manager_alerts = []
    if request.user.is_staff or request.user.is_superuser:
        manager_alerts = SmartNotifications.get_all_alerts_for_manager(request.user)

    return JsonResponse(
        {
            "success": True,
            "employee_alerts": employee_alerts,
            "manager_alerts": manager_alerts,
            "total_count": len(employee_alerts) + len(manager_alerts),
        }
    )


@login_required
def performance_insights_dashboard(request):
    """
    AI Performance Insights Dashboard for Managers
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to access this page.")
        return redirect("dashboard")

    company = request.company

    # Get all employees
    employees = Employee.objects.filter(company=company, is_active=True)

    performance_data = []

    for emp in employees:
        # Get attendance analysis
        attendance_analysis = AttendanceIntelligence.analyze_employee_patterns(
            emp, days=30
        )

        # Get leave patterns
        leave_patterns = LeavePrediction.analyze_leave_patterns(emp, months=3)

        # Calculate performance score (use risk_score, not score)
        performance_score = 100 - attendance_analysis.get("risk_score", 0)

        # Determine recommendation
        if attendance_analysis["risk_level"] == "CRITICAL":
            recommendation = "Immediate coaching required"
        elif attendance_analysis["risk_level"] == "HIGH":
            recommendation = "Performance review suggested"
        elif attendance_analysis["risk_level"] == "MEDIUM":
            recommendation = "Monitor closely"
        else:
            recommendation = "Performing well"

        performance_data.append(
            {
                "employee": emp,
                "attendance_score": performance_score,
                "risk_level": attendance_analysis["risk_level"],
                "late_count": attendance_analysis.get("late_logins", 0),
                "absence_count": attendance_analysis.get("absences", 0),
                "leave_count": leave_patterns.get("total_leaves", 0),
                "recommendation": recommendation,
            }
        )

    # Sort by performance score (lowest first - needs attention)
    performance_data.sort(key=lambda x: x["attendance_score"])

    context = {
        "performance_data": performance_data,
        "total_employees": len(performance_data),
    }

    return render(request, "ai_assistant/performance_insights.html", context)


@login_required
@require_http_methods(["POST"])
def chatbot_query_floating(request):
    """
    Handle floating chatbot queries with role-based responses
    """
    try:
        data = json.loads(request.body)
        query = data.get("query", "").lower()

        # Determine role from user object to ensure accuracy
        # Determine role safely
        role = "EMPLOYEE"
        user_role = getattr(request.user, "role", "EMPLOYEE")

        if user_role == "COMPANY_ADMIN" or request.user.is_superuser:
            role = "COMPANY_ADMIN"
        elif user_role == "MANAGER" or request.user.is_staff:
            role = "MANAGER"

        if not query:
            return JsonResponse({"error": "No query provided"}, status=400)

        # Get employee profile
        employee = safe_get_employee_profile(request.user)
        if not employee:
            return JsonResponse(
                {
                    "response": "I need your employee profile to assist you. Please contact your administrator.",
                    "show_escalation": True,
                }
            )

        # Get response from centralized HRChatbot
        bot_response = HRChatbot.get_response(
            query, employee, role=role, request=request
        )

        # Extract plain text answer for the floating widget
        if isinstance(bot_response, dict):
            response_text = bot_response.get("answer", "")
            action_data = bot_response.get("action", None)
        else:
            response_text = str(bot_response)
            action_data = None

        # Save chat history
        try:
            ChatMessage.objects.create(
                user=request.user, user_message=query, bot_response=response_text
            )
        except Exception as e:
            logger.warning("Error saving chat history", error=str(e))

        # Check if escalation is needed (if fallback was triggered or error)
        show_escalation = False
        if (
            "could not" in response_text.lower()
            or "unable to" in response_text.lower()
            or "sorry" in response_text.lower()
        ):
            show_escalation = True

        return JsonResponse(
            {
                "success": True,
                "response": response_text,
                "action": action_data,
                "show_escalation": show_escalation,
            }
        )

    except Exception as e:
        import traceback

        print(f"Floating chatbot error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse(
            {
                "response": f"I encountered an error: {str(e)}. Would you like to speak with human support?",
                "show_escalation": True,
            },
            status=500,
        )


@login_required
@require_http_methods(["POST"])
def escalate_support(request):
    """
    Escalate to human support - Create support ticket
    """
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        user_name = data.get("user_name")
        user_email = data.get("user_email")

        # Generate ticket ID
        import uuid

        ticket_id = f"HRMS-{uuid.uuid4().hex[:8].upper()}"

        # In a real implementation, you would:
        # 1. Create a support ticket in database
        # 2. Send email notification to support team
        # 3. Send confirmation email to user

        # For now, we'll just return success
        # You can integrate with your ticketing system here

        return JsonResponse(
            {
                "success": True,
                "ticket_id": ticket_id,
                "contact_email": user_email,
                "message": "Your request has been escalated to our support team.",
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_chat_history(request):
    """
    Get chat history for the logged-in user
    """
    try:
        messages = ChatMessage.objects.filter(user=request.user).order_by("timestamp")
        history = []
        for msg in messages:
            history.append(
                {
                    "text": msg.user_message,
                    "sender": "user",
                    "timestamp": msg.timestamp.strftime("%H:%M"),
                }
            )
            history.append(
                {
                    "text": msg.bot_response,
                    "sender": "bot",
                    "timestamp": msg.timestamp.strftime("%H:%M"),
                }
            )

        return JsonResponse(
            {
                "success": True,
                "history": history,
                "user_name": request.user.first_name or request.user.username,
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
