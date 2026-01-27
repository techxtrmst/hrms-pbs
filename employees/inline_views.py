
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Employee
from accounts.models import User

@login_required
def update_employee_inline(request, pk):
    """
    Handle inline updates from the employee detail page modals.
    """
    employee = get_object_or_404(Employee, pk=pk)
    
    # Permission check
    user = request.user
    is_admin = user.role == User.Role.COMPANY_ADMIN or user.is_superuser
    is_manager = user.role == User.Role.MANAGER and employee.manager == user
    
    if not (is_admin or is_manager):
        messages.error(request, "Permission denied")
        return redirect('employee_detail', pk=pk)
        
    if request.method == "POST":
        section = request.POST.get('section')
        
        try:
            if section == 'personal':
                employee.dob = request.POST.get('dob') or None
                employee.gender = request.POST.get('gender')
                employee.marital_status = request.POST.get('marital_status')
                employee.mobile_number = request.POST.get('mobile_number')
                employee.personal_email = request.POST.get('personal_email')
                
            elif section == 'job':
                employee.designation = request.POST.get('designation')
                employee.department = request.POST.get('department')
                # For foreign keys like manager, we need to handle carefully or just stick to simple fields for now
                # handling text fields first
                employee.badge_id = request.POST.get('badge_id')
                employee.work_type = request.POST.get('work_type')
                employee.date_of_joining = request.POST.get('date_of_joining') or None
                
            elif section == 'address':
                employee.current_address = request.POST.get('current_address')
                employee.permanent_address = request.POST.get('permanent_address')
                
            elif section == 'financial':
                employee.bank_name = request.POST.get('bank_name')
                employee.account_number = request.POST.get('account_number')
                employee.ifsc_code = request.POST.get('ifsc_code')
                employee.uan = request.POST.get('uan')
                employee.annual_ctc = request.POST.get('annual_ctc') or None
                employee.pf_enabled = request.POST.get('pf_enabled') == 'on'
                
            employee.save()
            messages.success(request, f"{section.title()} details updated successfully.")
            
        except Exception as e:
            messages.error(request, f"Error updating {section}: {str(e)}")
            
    return redirect('employee_detail', pk=pk)
