from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db import transaction
from .models import Employee, Attendance, LocationLog
from .forms import EmployeeCreationForm # We will create this next
from accounts.models import User
from django.http import JsonResponse
from django.utils import timezone
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

class CompanyAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == User.Role.COMPANY_ADMIN

class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'employees/employee_list.html'
    context_object_name = 'employees'

    def get_queryset(self):
        # Filter by current user's company
        return Employee.objects.filter(company=self.request.user.company)

class EmployeeCreateView(LoginRequiredMixin, CompanyAdminRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeCreationForm
    template_name = 'employees/employee_form.html'
    success_url = reverse_lazy('employee_list')

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        return super().form_valid(form)

class EmployeeUpdateView(LoginRequiredMixin, CompanyAdminRequiredMixin, UpdateView):
    model = Employee
    fields = ['designation', 'department', 'manager', 'date_of_joining'] # User fields handled separately ideally, but keeping simple for now
    template_name = 'employees/employee_form.html'
    success_url = reverse_lazy('employee_list')

    def get_queryset(self):
        return Employee.objects.filter(company=self.request.user.company)

class EmployeeDeleteView(LoginRequiredMixin, CompanyAdminRequiredMixin, DeleteView):
    model = Employee
    template_name = 'employees/employee_confirm_delete.html'
    success_url = reverse_lazy('employee_list')

    def get_queryset(self):
        return Employee.objects.filter(company=self.request.user.company)

# --- Attendance & Tracking Views ---

@csrf_exempt
@login_required
def clock_in(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat = data.get('latitude')
            lng = data.get('longitude')
            
            # Ensure employee profile exists
            if not hasattr(request.user, 'employee_profile'):
                 return JsonResponse({'status': 'error', 'message': 'No employee profile found'}, status=400)

            employee = request.user.employee_profile
            today = timezone.localdate()
            
            # Check if already clocked in
            attendance, created = Attendance.objects.get_or_create(
                employee=employee, 
                date=today,
                defaults={'status': 'Present'}
            )
            
            if attendance.clock_in:
                 return JsonResponse({'status': 'error', 'message': 'Already clocked in'})

            attendance.clock_in = timezone.now()
            attendance.location_in = f"{lat},{lng}"
            attendance.status = 'Present'
            attendance.save()
            
            return JsonResponse({'status': 'success', 'time': attendance.clock_in.strftime('%H:%M:%S')})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
@login_required
def clock_out(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat = data.get('latitude')
            lng = data.get('longitude')
            
            if not hasattr(request.user, 'employee_profile'):
                 return JsonResponse({'status': 'error', 'message': 'No employee profile found'}, status=400)
            
            employee = request.user.employee_profile
            today = timezone.localdate()
            
            try:
                attendance = Attendance.objects.get(employee=employee, date=today)
                attendance.clock_out = timezone.now()
                attendance.location_out = f"{lat},{lng}"
                attendance.save()
                return JsonResponse({'status': 'success', 'time': attendance.clock_out.strftime('%H:%M:%S')})
            except Attendance.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'No attendance record found for today'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
@login_required
def update_location(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat = data.get('latitude')
            lng = data.get('longitude')
            
            if not hasattr(request.user, 'employee_profile'):
                 return JsonResponse({'status': 'error', 'message': 'No employee profile found'}, status=400)

            employee = request.user.employee_profile
            LocationLog.objects.create(
                employee=employee,
                latitude=lat,
                longitude=lng
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

from django.shortcuts import redirect
from .models import EmployeeIDProof

@login_required
def employee_profile(request):
    user = request.user
    
    # Try to get or create employee profile if User is a Company Admin/Manager
    # This prevents the "blank page" issue for the initial admin user.
    try:
        employee = user.employee_profile
    except Exception:
        employee = None
    
    if not employee:
        if user.company:
            # Auto-create basic profile for Admin/Manager to avoid UI block
            employee = Employee.objects.create(
                user=user,
                company=user.company,
                designation="Administrator" if user.role == User.Role.COMPANY_ADMIN else "Employee",
                department="Management",
                badge_id=f"ADM{user.id}" # Simple fallback ID
            )
        else:
             # Fallback if no company (shouldn't happen for active users)
             # We must pass the 'content' block to a template that extends base.html
             return render(request, 'core/general_message.html', {
                 'title': 'Profile Not Found',
                 'message': 'No employee profile found. Please contact your administrator.'
             })

    id_proofs, created = EmployeeIDProof.objects.get_or_create(employee=employee)

    if request.method == 'POST':
        is_admin = request.user.role == User.Role.COMPANY_ADMIN
        
        # Helper to check if upload allowed
        def can_upload(current_file):
            return not current_file or is_admin

        if 'aadhar_front' in request.FILES:
            if can_upload(id_proofs.aadhar_front):
                id_proofs.aadhar_front = request.FILES['aadhar_front']
        
        if 'aadhar_back' in request.FILES:
            if can_upload(id_proofs.aadhar_back):
                id_proofs.aadhar_back = request.FILES['aadhar_back']
                
        if 'pan_card' in request.FILES:
            if can_upload(id_proofs.pan_card):
                id_proofs.pan_card = request.FILES['pan_card']
        
        id_proofs.save()
        
        # Deletion logic for Admins
        if is_admin:
            if request.POST.get('delete_aadhar_front') == 'on':
                id_proofs.aadhar_front.delete(save=False)
                id_proofs.aadhar_front = None
            if request.POST.get('delete_aadhar_back') == 'on':
                id_proofs.aadhar_back.delete(save=False)
                id_proofs.aadhar_back = None
            if request.POST.get('delete_pan_card') == 'on':
                id_proofs.pan_card.delete(save=False)
                id_proofs.pan_card = None
            id_proofs.save()

        return redirect('employee_profile')

    return render(request, 'employees/employee_profile.html', {
        'employee': employee,
        'id_proofs': id_proofs,
        'is_admin': request.user.role == User.Role.COMPANY_ADMIN
    })
