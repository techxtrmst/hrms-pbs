from django.urls import path
from . import views

app_name = 'handbooks'

urlpatterns = [
    # Employee views
    path('', views.handbook_list, name='handbook_list'),
    path('<int:handbook_id>/', views.handbook_detail, name='handbook_detail'),
    path('<int:handbook_id>/acknowledge/', views.acknowledge_handbook, name='acknowledge_handbook'),
    
    # Admin views
    path('admin/list/', views.admin_handbook_list, name='admin_handbook_list'),
    path('admin/create/', views.admin_handbook_create, name='admin_handbook_create'),
    path('admin/<int:handbook_id>/edit/', views.admin_handbook_edit, name='admin_handbook_edit'),
    path('admin/<int:handbook_id>/report/', views.admin_acknowledgment_report, name='admin_acknowledgment_report'),
]
