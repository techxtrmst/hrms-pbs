from django.urls import path

from .views import (
    ActivityDashboardView,
    ActivityIngestView,
    AppActivityDetailView,
    BrowserActivityDetailView,
    HeartbeatView,
    download_agent,
)

urlpatterns = [
    path("api/sync/", ActivityIngestView.as_view(), name="activity-sync"),
    path("api/heartbeat/<int:employee_id>/", HeartbeatView.as_view(), name="web-heartbeat"),
    path("dashboard/", ActivityDashboardView.as_view(), name="activity-dashboard"),
    path("urls/", BrowserActivityDetailView.as_view(), name="browser-activity-detail"),
    path("apps/", AppActivityDetailView.as_view(), name="app-activity-detail"),
    path("download-agent/", download_agent, name="download-agent"),
]
