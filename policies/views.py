from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Q, Count
from .models import Policy, PolicySection, PolicyAcknowledgment, PolicyAttachment
from employees.models import Employee


@login_required
def policy_list(request):
    """
    Display policies for the logged-in employee based on their location
    """
    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        return HttpResponseForbidden("You must be an employee to view policies.")

    # Get published policies for employee's location
    policies = (
        Policy.objects.filter(
            company=employee.company,
            location=employee.location,
            is_published=True,
            effective_date__lte=timezone.now().date(),
        )
        .select_related("section", "location", "created_by")
        .order_by("section__order", "title")
    )

    # Get sections for grouping
    sections = PolicySection.objects.filter(
        company=employee.company, is_active=True
    ).order_by("order")

    # Group policies by section
    policies_by_section = {}
    for section in sections:
        section_policies = policies.filter(section=section)
        if section_policies.exists():
            policies_by_section[section] = section_policies

    # Policies without section
    no_section_policies = policies.filter(section__isnull=True)

    # Get acknowledgment status
    acknowledgments = PolicyAcknowledgment.objects.filter(
        employee=employee, policy__in=policies
    ).values_list("policy_id", "acknowledged")
    acknowledgment_dict = dict(acknowledgments)

    context = {
        "policies_by_section": policies_by_section,
        "no_section_policies": no_section_policies,
        "acknowledgment_dict": acknowledgment_dict,
        "employee": employee,
    }

    return render(request, "policies/policy_list.html", context)


@login_required
def policy_detail(request, policy_id):
    """
    Display detailed view of a specific policy
    """
    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        return HttpResponseForbidden("You must be an employee to view policies.")

    # Get policy and verify access
    policy = get_object_or_404(
        Policy,
        id=policy_id,
        company=employee.company,
        location=employee.location,
        is_published=True,
    )

    # Get or create acknowledgment record
    acknowledgment, created = PolicyAcknowledgment.objects.get_or_create(
        policy=policy, employee=employee
    )

    # Get attachments
    attachments = policy.attachments.all()

    context = {
        "policy": policy,
        "acknowledgment": acknowledgment,
        "attachments": attachments,
        "employee": employee,
    }

    return render(request, "policies/policy_detail.html", context)


@login_required
def acknowledge_policy(request, policy_id):
    """
    Mark a policy as acknowledged by the employee
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        return JsonResponse({"success": False, "error": "Employee profile not found"})

    # Get policy and verify access
    policy = get_object_or_404(
        Policy,
        id=policy_id,
        company=employee.company,
        location=employee.location,
        is_published=True,
    )

    # Get or create acknowledgment
    acknowledgment, created = PolicyAcknowledgment.objects.get_or_create(
        policy=policy, employee=employee
    )

    # Update acknowledgment
    acknowledgment.acknowledged = True
    acknowledgment.acknowledged_at = timezone.now()

    # Get IP address
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        acknowledgment.ip_address = x_forwarded_for.split(",")[0]
    else:
        acknowledgment.ip_address = request.META.get("REMOTE_ADDR")

    # Get user agent
    acknowledgment.user_agent = request.META.get("HTTP_USER_AGENT", "")
    acknowledgment.save()

    return JsonResponse(
        {
            "success": True,
            "acknowledged_at": acknowledgment.acknowledged_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
    )


# Admin views for managing policies
@login_required
def admin_policy_list(request):
    """
    Admin view to list and manage policies (location-based access)
    """
    # Check if user is admin
    if request.user.role not in ["SUPERADMIN", "COMPANY_ADMIN"]:
        return HttpResponseForbidden("You don't have permission to access this page.")

    # Filter policies based on admin's location
    policies = Policy.objects.select_related(
        "company", "location", "section", "created_by", "updated_by"
    ).annotate(
        acknowledgment_count=Count(
            "acknowledgments", filter=Q(acknowledgments__acknowledged=True)
        )
    )

    if request.user.role == "COMPANY_ADMIN":
        policies = policies.filter(company=request.user.company)

        # Further filter by location if admin has a specific location
        if (
            hasattr(request.user, "employee_profile")
            and request.user.employee_profile.location
        ):
            policies = policies.filter(location=request.user.employee_profile.location)

    policies = policies.order_by("-updated_at")

    context = {"policies": policies, "active_tab": "policies"}

    return render(request, "policies/admin_policy_list.html", context)


@login_required
def admin_policy_create(request):
    """
    Admin view to create a new policy
    """
    # Check if user is admin
    if request.user.role not in ["SUPERADMIN", "COMPANY_ADMIN"]:
        return HttpResponseForbidden("You don't have permission to access this page.")

    from .forms import PolicyForm

    # Auto-initialize default sections if they don't exist for this company
    if request.user.role == "COMPANY_ADMIN" and request.user.company:
        if not PolicySection.objects.filter(company=request.user.company).exists():
            default_sections = [
                {"title": "Leave Policy", "icon": "🌴", "order": 1},
                {"title": "HR Policy", "icon": "👥", "order": 2},
                {"title": "IT Policy", "icon": "💻", "order": 3},
                {"title": "General", "icon": "📋", "order": 4},
            ]
            for section_data in default_sections:
                PolicySection.objects.create(
                    company=request.user.company, **section_data
                )

    if request.method == "POST":
        form = PolicyForm(request.POST, user=request.user)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.company = request.user.company
            policy.created_by = request.user
            policy.updated_by = request.user
            policy.save()
            return redirect("policies:admin_policy_list")
    else:
        form = PolicyForm(user=request.user)

    context = {"form": form, "title": "Create Policy"}

    return render(request, "policies/admin_policy_form.html", context)


@login_required
def admin_policy_edit(request, policy_id):
    """
    Admin view to edit an existing policy
    """
    # Check if user is admin
    if request.user.role not in ["SUPERADMIN", "COMPANY_ADMIN"]:
        return HttpResponseForbidden("You don't have permission to access this page.")

    # Get policy with location-based access control
    policy = get_object_or_404(Policy, id=policy_id)

    # Verify admin has access to this policy's location
    if request.user.role == "COMPANY_ADMIN":
        if policy.company != request.user.company:
            return HttpResponseForbidden(
                "You don't have permission to edit this policy."
            )

        if (
            hasattr(request.user, "employee_profile")
            and request.user.employee_profile.location
        ):
            if policy.location != request.user.employee_profile.location:
                return HttpResponseForbidden(
                    "You don't have permission to edit this policy."
                )

    from .forms import PolicyForm

    if request.method == "POST":
        form = PolicyForm(request.POST, instance=policy, user=request.user)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.updated_by = request.user
            policy.save()
            return redirect("policies:admin_policy_list")
    else:
        form = PolicyForm(instance=policy, user=request.user)

    context = {
        "form": form,
        "policy": policy,
        "title": "Edit Policy",
        "editing": True,
    }

    return render(request, "policies/admin_policy_form.html", context)


@login_required
def admin_acknowledgment_report(request, policy_id):
    """
    Admin view to see who has acknowledged a policy
    """
    # Check if user is admin
    if request.user.role not in ["SUPERADMIN", "COMPANY_ADMIN"]:
        return HttpResponseForbidden("You don't have permission to access this page.")

    policy = get_object_or_404(Policy, id=policy_id)

    # Verify access
    if request.user.role == "COMPANY_ADMIN":
        if policy.company != request.user.company:
            return HttpResponseForbidden(
                "You don't have permission to view this report."
            )

        if (
            hasattr(request.user, "employee_profile")
            and request.user.employee_profile.location
        ):
            if policy.location != request.user.employee_profile.location:
                return HttpResponseForbidden(
                    "You don't have permission to view this report."
                )

    # Get all employees at this location
    employees = Employee.objects.filter(
        company=policy.company, location=policy.location, is_active=True
    ).select_related("user")

    # Get acknowledgments
    acknowledgments = PolicyAcknowledgment.objects.filter(policy=policy).select_related(
        "employee__user"
    )

    acknowledgment_dict = {ack.employee_id: ack for ack in acknowledgments}

    # Build employee acknowledgment data
    employee_data = []
    for employee in employees:
        ack = acknowledgment_dict.get(employee.id)
        employee_data.append(
            {
                "employee": employee,
                "acknowledgment": ack,
                "acknowledged": ack.acknowledged if ack else False,
                "acknowledged_at": ack.acknowledged_at
                if ack and ack.acknowledged
                else None,
            }
        )

    context = {
        "policy": policy,
        "employee_data": employee_data,
        "total_employees": len(employee_data),
        "acknowledged_count": sum(1 for ed in employee_data if ed["acknowledged"]),
    }

    return render(request, "policies/admin_acknowledgment_report.html", context)
