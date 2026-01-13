from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Q, Count
from .models import Handbook, HandbookSection, HandbookAcknowledgment, HandbookAttachment
from employees.models import Employee


@login_required
def handbook_list(request):
    """
    Display handbooks for the logged-in employee based on their location
    """
    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        return HttpResponseForbidden("You must be an employee to view handbooks.")

    # Get published handbooks for employee's location
    handbooks = Handbook.objects.filter(
        company=employee.company,
        location=employee.location,
        is_published=True,
        effective_date__lte=timezone.now().date()
    ).select_related('section', 'location', 'created_by').order_by('section__order', 'title')

    # Get sections for grouping
    sections = HandbookSection.objects.filter(
        company=employee.company,
        is_active=True
    ).order_by('order')

    # Group handbooks by section
    handbooks_by_section = {}
    for section in sections:
        section_handbooks = handbooks.filter(section=section)
        if section_handbooks.exists():
            handbooks_by_section[section] = section_handbooks

    # Handbooks without section
    no_section_handbooks = handbooks.filter(section__isnull=True)

    # Get acknowledgment status
    acknowledgments = HandbookAcknowledgment.objects.filter(
        employee=employee,
        handbook__in=handbooks
    ).values_list('handbook_id', 'acknowledged')
    acknowledgment_dict = dict(acknowledgments)

    context = {
        'handbooks_by_section': handbooks_by_section,
        'no_section_handbooks': no_section_handbooks,
        'acknowledgment_dict': acknowledgment_dict,
        'employee': employee,
    }

    return render(request, 'handbooks/handbook_list.html', context)


@login_required
def handbook_detail(request, handbook_id):
    """
    Display detailed view of a specific handbook
    """
    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        return HttpResponseForbidden("You must be an employee to view handbooks.")

    # Get handbook and verify access
    handbook = get_object_or_404(
        Handbook,
        id=handbook_id,
        company=employee.company,
        location=employee.location,
        is_published=True
    )

    # Get or create acknowledgment record
    acknowledgment, created = HandbookAcknowledgment.objects.get_or_create(
        handbook=handbook,
        employee=employee
    )

    # Get attachments
    attachments = handbook.attachments.all()

    context = {
        'handbook': handbook,
        'acknowledgment': acknowledgment,
        'attachments': attachments,
        'employee': employee,
    }

    return render(request, 'handbooks/handbook_detail.html', context)


@login_required
def acknowledge_handbook(request, handbook_id):
    """
    Mark a handbook as acknowledged by the employee
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee profile not found'})

    # Get handbook and verify access
    handbook = get_object_or_404(
        Handbook,
        id=handbook_id,
        company=employee.company,
        location=employee.location,
        is_published=True
    )

    # Get or create acknowledgment
    acknowledgment, created = HandbookAcknowledgment.objects.get_or_create(
        handbook=handbook,
        employee=employee
    )

    # Update acknowledgment
    acknowledgment.acknowledged = True
    acknowledgment.acknowledged_at = timezone.now()
    
    # Get IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        acknowledgment.ip_address = x_forwarded_for.split(',')[0]
    else:
        acknowledgment.ip_address = request.META.get('REMOTE_ADDR')
    
    # Get user agent
    acknowledgment.user_agent = request.META.get('HTTP_USER_AGENT', '')
    acknowledgment.save()

    return JsonResponse({
        'success': True,
        'acknowledged_at': acknowledgment.acknowledged_at.strftime('%Y-%m-%d %H:%M:%S')
    })


# Admin views for managing handbooks
@login_required
def admin_handbook_list(request):
    """
    Admin view to list and manage handbooks (location-based access)
    """
    # Check if user is admin
    if request.user.role not in ['SUPERADMIN', 'COMPANY_ADMIN']:
        return HttpResponseForbidden("You don't have permission to access this page.")

    # Filter handbooks based on admin's location
    handbooks = Handbook.objects.select_related(
        'company', 'location', 'section', 'created_by', 'updated_by'
    ).annotate(
        acknowledgment_count=Count('acknowledgments', filter=Q(acknowledgments__acknowledged=True))
    )

    if request.user.role == 'COMPANY_ADMIN':
        handbooks = handbooks.filter(company=request.user.company)
        
        # Further filter by location if admin has a specific location
        if hasattr(request.user, 'employee_profile') and request.user.employee_profile.location:
            handbooks = handbooks.filter(location=request.user.employee_profile.location)

    handbooks = handbooks.order_by('-updated_at')

    context = {
        'handbooks': handbooks,
    }

    return render(request, 'handbooks/admin_handbook_list.html', context)


@login_required
def admin_handbook_create(request):
    """
    Admin view to create a new handbook
    """
    # Check if user is admin
    if request.user.role not in ['SUPERADMIN', 'COMPANY_ADMIN']:
        return HttpResponseForbidden("You don't have permission to access this page.")

    from .forms import HandbookForm

    if request.method == 'POST':
        form = HandbookForm(request.POST, user=request.user)
        if form.is_valid():
            handbook = form.save(commit=False)
            handbook.company = request.user.company
            handbook.created_by = request.user
            handbook.updated_by = request.user
            handbook.save()
            return redirect('handbooks:admin_handbook_list')
    else:
        form = HandbookForm(user=request.user)

    context = {
        'form': form,
        'title': 'Create Handbook'
    }

    return render(request, 'handbooks/admin_handbook_form.html', context)


@login_required
def admin_handbook_edit(request, handbook_id):
    """
    Admin view to edit an existing handbook
    """
    # Check if user is admin
    if request.user.role not in ['SUPERADMIN', 'COMPANY_ADMIN']:
        return HttpResponseForbidden("You don't have permission to access this page.")

    # Get handbook with location-based access control
    handbook = get_object_or_404(Handbook, id=handbook_id)

    # Verify admin has access to this handbook's location
    if request.user.role == 'COMPANY_ADMIN':
        if handbook.company != request.user.company:
            return HttpResponseForbidden("You don't have permission to edit this handbook.")
        
        if hasattr(request.user, 'employee_profile') and request.user.employee_profile.location:
            if handbook.location != request.user.employee_profile.location:
                return HttpResponseForbidden("You don't have permission to edit this handbook.")

    from .forms import HandbookForm

    if request.method == 'POST':
        form = HandbookForm(request.POST, instance=handbook, user=request.user)
        if form.is_valid():
            handbook = form.save(commit=False)
            handbook.updated_by = request.user
            handbook.save()
            return redirect('handbooks:admin_handbook_list')
    else:
        form = HandbookForm(instance=handbook, user=request.user)

    context = {
        'form': form,
        'handbook': handbook,
        'title': 'Edit Handbook',
        'editing': True,
    }

    return render(request, 'handbooks/admin_handbook_form.html', context)


@login_required
def admin_acknowledgment_report(request, handbook_id):
    """
    Admin view to see who has acknowledged a handbook
    """
    # Check if user is admin
    if request.user.role not in ['SUPERADMIN', 'COMPANY_ADMIN']:
        return HttpResponseForbidden("You don't have permission to access this page.")

    handbook = get_object_or_404(Handbook, id=handbook_id)

    # Verify access
    if request.user.role == 'COMPANY_ADMIN':
        if handbook.company != request.user.company:
            return HttpResponseForbidden("You don't have permission to view this report.")
        
        if hasattr(request.user, 'employee_profile') and request.user.employee_profile.location:
            if handbook.location != request.user.employee_profile.location:
                return HttpResponseForbidden("You don't have permission to view this report.")

    # Get all employees at this location
    employees = Employee.objects.filter(
        company=handbook.company,
        location=handbook.location,
        is_active=True
    ).select_related('user')

    # Get acknowledgments
    acknowledgments = HandbookAcknowledgment.objects.filter(
        handbook=handbook
    ).select_related('employee__user')

    acknowledgment_dict = {ack.employee_id: ack for ack in acknowledgments}

    # Build employee acknowledgment data
    employee_data = []
    for employee in employees:
        ack = acknowledgment_dict.get(employee.id)
        employee_data.append({
            'employee': employee,
            'acknowledgment': ack,
            'acknowledged': ack.acknowledged if ack else False,
            'acknowledged_at': ack.acknowledged_at if ack and ack.acknowledged else None,
        })

    context = {
        'handbook': handbook,
        'employee_data': employee_data,
        'total_employees': len(employee_data),
        'acknowledged_count': sum(1 for ed in employee_data if ed['acknowledged']),
    }

    return render(request, 'handbooks/admin_acknowledgment_report.html', context)
