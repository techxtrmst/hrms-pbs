"""URL configuration for the observability app."""

from django.urls import path

from . import views

app_name = "observability"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    # Error views
    path("errors/", views.ErrorListView.as_view(), name="error_list"),
    path("errors/<uuid:pk>/", views.ErrorDetailView.as_view(), name="error_detail"),
    path("errors/groups/", views.ErrorGroupListView.as_view(), name="error_group_list"),
    path("errors/groups/<int:pk>/", views.ErrorGroupDetailView.as_view(), name="error_group_detail"),
    # Request logs
    path("requests/", views.RequestLogListView.as_view(), name="request_list"),
    path("requests/<uuid:pk>/", views.RequestLogDetailView.as_view(), name="request_detail"),
    # Performance
    path("performance/", views.PerformanceView.as_view(), name="performance"),
    path("performance/slow/", views.SlowRequestsView.as_view(), name="slow_requests"),
    # API endpoints for charts/data
    path("api/stats/", views.StatsAPIView.as_view(), name="api_stats"),
    path("api/errors/chart/", views.ErrorChartAPIView.as_view(), name="api_error_chart"),
    path("api/requests/chart/", views.RequestChartAPIView.as_view(), name="api_request_chart"),
    path("api/performance/chart/", views.PerformanceChartAPIView.as_view(), name="api_performance_chart"),
]
