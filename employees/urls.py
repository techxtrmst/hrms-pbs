from django.urls import path
from . import views

urlpatterns = [
    path('', views.EmployeeListView.as_view(), name='employee_list'),
    path('add/', views.EmployeeCreateView.as_view(), name='employee_add'),
    path('<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_edit'),
    path('<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='employee_delete'),
    
    path('employee-profile/', views.employee_profile, name='employee_profile'),
    
    # API endpoints for attendance
    path('api/clock-in/', views.clock_in, name='api_clock_in'),
    path('api/clock-out/', views.clock_out, name='api_clock_out'),
    path('api/update-location/', views.update_location, name='api_update_location'),
]
