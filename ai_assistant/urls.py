from django.urls import path
from . import views

urlpatterns = [
    # AI Features Hub
    path("", views.ai_features_hub, name="ai_hub"),
    # Attrition Risk Dashboard
    path("attrition-risk/", views.attrition_dashboard, name="attrition_dashboard"),
    path(
        "attrition-risk/<int:employee_id>/",
        views.employee_risk_detail,
        name="employee_risk_detail",
    ),
    # HR Chatbot
    path("chatbot/", views.chatbot_page, name="chatbot_page"),
    path("chatbot/query/", views.chatbot_query, name="chatbot_query"),
    # Resume Parser
    path("resume-parser/", views.resume_parser_view, name="resume_parser"),
    path(
        "resume-parser/result/<int:job_id>/",
        views.resume_parser_result,
        name="resume_parser_result",
    ),
    # Attendance Intelligence
    path(
        "attendance-intelligence/",
        views.attendance_intelligence_dashboard,
        name="attendance_intelligence",
    ),
    path(
        "attendance-intelligence/<int:employee_id>/",
        views.employee_attendance_detail,
        name="employee_attendance_detail",
    ),
    # Leave Prediction
    path(
        "leave-prediction/", views.leave_prediction_dashboard, name="leave_prediction"
    ),
    path("my-leave-insights/", views.my_leave_insights, name="my_leave_insights"),
    # Smart Notifications
    path(
        "notifications/",
        views.smart_notifications_dashboard,
        name="smart_notifications",
    ),
    path("api/notifications/", views.get_notifications_api, name="notifications_api"),
    # Performance Insights
    path(
        "performance-insights/",
        views.performance_insights_dashboard,
        name="performance_insights",
    ),
    # Floating Chatbot
    path(
        "chatbot/floating/query/",
        views.chatbot_query_floating,
        name="chatbot_query_floating",
    ),
    path("chatbot/history/", views.get_chat_history, name="get_chat_history"),
    path("support/escalate/", views.escalate_support, name="escalate_support"),
]
