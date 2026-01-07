# Emergency Contact Management Views
# Add these to employees/views.py

from django.forms import modelformset_factory
from .models import EmergencyContact
from .forms import EmergencyContactForm

@login_required
def manage_emergency_contacts(request):
    """
    View to manage emergency contacts for the logged-in employee
    """
    try:
        employee = request.user.employee_profile
    except:
        messages.error(request, "Employee profile not found.")
        return redirect('dashboard')
    
    EmergencyContactFormSet = modelformset_factory(
        EmergencyContact,
        form=EmergencyContactForm,
        extra=1,  # Show 1 empty form by default
        can_delete=True
    )
    
    if request.method == 'POST':
        formset = EmergencyContactFormSet(
            request.POST,
            queryset=EmergencyContact.objects.filter(employee=employee)
        )
        
        if formset.is_valid():
            instances = formset.save(commit=False)
            
            # Assign employee to new contacts
            for instance in instances:
                instance.employee = employee
                instance.save()
            
            # Handle deletions
            for obj in formset.deleted_objects:
                obj.delete()
            
            messages.success(request, "Emergency contacts updated successfully!")
            return redirect('employee_profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        formset = EmergencyContactFormSet(
            queryset=EmergencyContact.objects.filter(employee=employee)
        )
    
    return render(request, 'employees/manage_emergency_contacts.html', {
        'formset': formset,
        'employee': employee
    })


@login_required
@require_http_methods(["POST"])
def add_emergency_contact(request):
    """
    AJAX endpoint to add a new emergency contact
    """
    try:
        employee = request.user.employee_profile
        
        form = EmergencyContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.employee = employee
            contact.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Emergency contact added successfully',
                'contact': {
                    'id': contact.id,
                    'name': contact.name,
                    'phone_number': contact.phone_number,
                    'relationship': contact.relationship,
                    'is_primary': contact.is_primary
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid data',
                'errors': form.errors
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def delete_emergency_contact(request, contact_id):
    """
    AJAX endpoint to delete an emergency contact
    """
    try:
        employee = request.user.employee_profile
        contact = EmergencyContact.objects.get(id=contact_id, employee=employee)
        contact.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Emergency contact deleted successfully'
        })
    except EmergencyContact.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Contact not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def update_emergency_contact(request, contact_id):
    """
    AJAX endpoint to update an emergency contact
    """
    try:
        employee = request.user.employee_profile
        contact = EmergencyContact.objects.get(id=contact_id, employee=employee)
        
        form = EmergencyContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Emergency contact updated successfully',
                'contact': {
                    'id': contact.id,
                    'name': contact.name,
                    'phone_number': contact.phone_number,
                    'relationship': contact.relationship,
                    'is_primary': contact.is_primary
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid data',
                'errors': form.errors
            }, status=400)
    except EmergencyContact.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Contact not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
