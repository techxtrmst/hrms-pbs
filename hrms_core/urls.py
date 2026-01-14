from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("employees/", include("employees.urls")),
    path("companies/", include("companies.urls")),
    path("api/", include("core.api_urls")),
    path("accounts/", include("accounts.urls")),
    path("superadmin/", include("superadmin.urls")),
    path("ai/", include("ai_assistant.urls")),  # AI-powered features
    path("handbooks/", include("handbooks.urls", namespace="handbooks")),  # Employee Handbooks
    path("policies/", include("policies.urls", namespace="policies")),  # Company Policies
    path(
        "accounts/", include("django.contrib.auth.urls")
    ),  # For password reset etc if needed
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
