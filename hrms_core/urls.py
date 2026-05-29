from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("hijack/", include("hijack.urls")),  # User impersonation
    path("observability/", include("observability.urls", namespace="observability")),  # Observability dashboard
    path("", include("core.urls")),
    path("employees/", include("employees.urls")),
    path("companies/", include("companies.urls")),
    path("api/", include("core.api_urls")),
    # Company API endpoints
    path(
        "api/companies/<int:company_id>/locations/",
        lambda request, company_id: __import__(
            "companies.api_views", fromlist=["get_company_locations"]
        ).get_company_locations(request, company_id),
    ),
    path(
        "api/companies/<int:company_id>/policies/",
        lambda request, company_id: __import__(
            "companies.api_views", fromlist=["get_company_policies"]
        ).get_company_policies(request, company_id),
    ),
    path(
        "api/companies/<int:company_id>/employee-id-format/",
        lambda request, company_id: __import__(
            "companies.api_views", fromlist=["get_employee_id_format"]
        ).get_employee_id_format(request, company_id),
    ),
    path("accounts/", include("accounts.urls")),
    path("superadmin/", include("superadmin.urls")),
    path("finance/", include("finance_portal.urls", namespace="finance_portal")),
    path("ai/", include("ai_assistant.urls")),  # AI-powered features
    path("handbooks/", include("handbooks.urls", namespace="handbooks")),  # Employee Handbooks
    path("policies/", include("policies.urls", namespace="policies")),  # Company Policies
    path("activity-tracking/", include("activity_monitoring.urls")),  # Screen time activity tracking
    path("accounts/", include("django.contrib.auth.urls")),  # For password reset etc if needed
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
