from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from employees.api import EmployeeViewSet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint for Docker/deployment monitoring."""
    return JsonResponse({"status": "healthy", "service": "hrms-backend"})


router = DefaultRouter()
router.register(r"employees", EmployeeViewSet, basename="api-employee")

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("", include(router.urls)),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
