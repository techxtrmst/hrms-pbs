from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Employee, SupportTicket, TicketMessage


@login_required
def support_ticket_list(request):
    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        messages.error(request, "Employee profile not found.")
        return redirect("dashboard")

    # Designated global support agent, company admin, HR, or manager can view tickets
    is_global_support = employee.is_support_agent
    is_company_support = (
        request.user.role in ["COMPANY_ADMIN", "SUPERADMIN", "MANAGER", "EMPLOYEE_MANAGER"]
        or employee.assigned_tickets.exists()
    )

    if is_global_support:
        # Global support agent sees all tickets across all companies in the platform
        tickets_qs = SupportTicket.objects.all()
        # Populates assignee list with only active Support Agents
        employees_list = Employee.objects.filter(is_support_agent=True, is_active=True)
    elif is_company_support:
        # Company admins/managers see only their company's tickets
        tickets_qs = SupportTicket.objects.filter(employee__company=employee.company)
        # Populates assignee list with only active Support Agents
        employees_list = Employee.objects.filter(is_support_agent=True, is_active=True)
    else:
        # Regular employees see only their own tickets
        tickets_qs = SupportTicket.objects.filter(employee=employee)
        employees_list = None

    # Jira-style status classification
    open_tickets = tickets_qs.filter(status="OPEN")
    inprogress_tickets = tickets_qs.filter(status="IN_PROGRESS")
    done_tickets = tickets_qs.filter(status="DONE")

    context = {
        "open_tickets": open_tickets,
        "inprogress_tickets": inprogress_tickets,
        "done_tickets": done_tickets,
        "employees_list": employees_list,
        "is_support_staff": is_global_support or is_company_support,
        "categories": SupportTicket.CATEGORY_CHOICES,
        "priorities": SupportTicket.PRIORITY_CHOICES,
    }
    return render(request, "employees/support_ticket_list.html", context)


@login_required
def support_ticket_create(request):
    if request.method == "POST":
        try:
            employee = request.user.employee_profile
        except Employee.DoesNotExist:
            messages.error(request, "Employee profile not found.")
            return redirect("support_ticket_list")

        subject = request.POST.get("subject")
        description = request.POST.get("description")
        category = request.POST.get("category", "GENERAL")
        priority = request.POST.get("priority", "MEDIUM")

        if not subject or not description:
            messages.error(request, "Subject and Description are required.")
            return redirect("support_ticket_list")

        # Find global designated support agent across all companies
        support_agent = Employee.objects.filter(is_support_agent=True).first()

        ticket = SupportTicket.objects.create(
            employee=employee,
            assigned_to=support_agent,
            subject=subject,
            description=description,
            category=category,
            priority=priority,
            status="OPEN",
        )

        # Notify the global Support Agent via Email
        if support_agent and support_agent.user.email:
            from django.conf import settings
            from django.core.mail import send_mail

            try:
                subject_mail = f"[HRMS Support] New Ticket #{ticket.id} Assigned: {ticket.subject}"
                message_mail = (
                    f"Hello {support_agent.user.get_full_name()},\n\n"
                    f"A new support ticket has been raised by {employee.user.get_full_name()} ({employee.designation} - {employee.company.name}) and automatically assigned to you.\n\n"
                    f"Ticket Summary:\n"
                    f"- Ticket ID: #{ticket.id}\n"
                    f"- Subject: {ticket.subject}\n"
                    f"- Category: {ticket.get_category_display()}\n"
                    f"- Priority: {ticket.get_priority_display()}\n"
                    f"- Description:\n{ticket.description}\n\n"
                    f"Please log in to the HRMS Helpdesk to manage this ticket.\n\n"
                    f"Warm regards,\n"
                    f"HRMS Helpdesk Team"
                )
                send_mail(
                    subject_mail,
                    message_mail,
                    settings.DEFAULT_FROM_EMAIL,
                    [support_agent.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                from loguru import logger

                logger.error(f"Error sending email to support agent: {e}")

        messages.success(request, f"Support Ticket #{ticket.id} created successfully!")
    return redirect("support_ticket_list")


@login_required
def support_ticket_detail(request, ticket_id):
    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        messages.error(request, "Employee profile not found.")
        return redirect("dashboard")

    # Fetch the ticket
    ticket = get_object_or_404(SupportTicket, id=ticket_id)

    # Global agent, company admins/managers/HR, or assigned agent are marked as support staff
    is_support_staff = (
        request.user.role in ["COMPANY_ADMIN", "SUPERADMIN", "MANAGER", "EMPLOYEE_MANAGER"]
        or ticket.assigned_to == employee
        or employee.is_support_agent
    )

    # Permission check: must belong to same company OR be part of global support staff
    if ticket.employee.company != employee.company and not is_support_staff:
        return HttpResponseForbidden("You do not have permission to view this ticket.")

    # Regular employees can only view their own tickets
    if not is_support_staff and ticket.employee != employee:
        return HttpResponseForbidden("You do not have permission to view this ticket.")

    # Handle posting messages (chat comments)
    if request.method == "POST":
        message_text = request.POST.get("message")
        if message_text:
            TicketMessage.objects.create(ticket=ticket, sender=employee, message=message_text)
            messages.success(request, "Reply sent successfully!")
            return redirect("support_ticket_detail", ticket_id=ticket.id)

    # List of support members (Only show employees flagged as support agents!)
    support_agents = Employee.objects.filter(is_support_agent=True, is_active=True)

    context = {
        "ticket": ticket,
        "messages": ticket.messages.all(),
        "is_support_staff": is_support_staff,
        "support_agents": support_agents,
    }
    return render(request, "employees/support_ticket_detail.html", context)


@login_required
def support_ticket_update_status(request, ticket_id):
    if request.method == "POST":
        try:
            employee = request.user.employee_profile
        except Employee.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Employee profile not found."}, status=400)

        ticket = get_object_or_404(SupportTicket, id=ticket_id)

        is_support_staff = (
            request.user.role in ["COMPANY_ADMIN", "SUPERADMIN", "MANAGER", "EMPLOYEE_MANAGER"]
            or ticket.assigned_to == employee
            or employee.is_support_agent
        )

        # Permission check: must belong to same company OR be part of global support staff
        if ticket.employee.company != employee.company and not is_support_staff:
            return JsonResponse({"status": "error", "message": "Access denied."}, status=403)

        if not is_support_staff and ticket.employee != employee:
            return JsonResponse({"status": "error", "message": "Access denied."}, status=403)

        new_status = request.POST.get("status")
        if new_status in dict(SupportTicket.STATUS_CHOICES):
            old_status = ticket.status
            ticket.status = new_status
            ticket.save()

            # Auto comment about status change
            status_display = ticket.get_status_display()
            TicketMessage.objects.create(
                ticket=ticket, sender=employee, message=f"🔄 Status updated to *{status_display}*"
            )

            # Send Email Notification to creator on resolution (DONE)
            if new_status == "DONE" and old_status != "DONE" and ticket.employee.user.email:
                from django.conf import settings
                from django.core.mail import send_mail

                try:
                    subject_mail = f"[HRMS Support] Resolved: Ticket #{ticket.id} - {ticket.subject}"
                    message_mail = (
                        f"Hello {ticket.employee.user.get_full_name()},\n\n"
                        f"Your support ticket #{ticket.id} has been marked as Resolved / Done by our Support Team.\n\n"
                        f"Ticket Details:\n"
                        f"- Subject: {ticket.subject}\n"
                        f"- Status: Resolved / Done\n\n"
                        f"Thank you for your patience. If you have any further questions, feel free to update the chat within the Helpdesk portal.\n\n"
                        f"Warm regards,\n"
                        f"HRMS Helpdesk Team"
                    )
                    send_mail(
                        subject_mail,
                        message_mail,
                        settings.DEFAULT_FROM_EMAIL,
                        [ticket.employee.user.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    from loguru import logger

                    logger.error(f"Error sending resolved email to creator: {e}")

            return JsonResponse({"status": "success", "new_status": status_display})

        return JsonResponse({"status": "error", "message": "Invalid status option."}, status=400)

    return JsonResponse({"status": "error", "message": "POST request expected."}, status=405)


@login_required
def support_ticket_assign(request, ticket_id):
    if request.method == "POST":
        try:
            employee = request.user.employee_profile
        except Employee.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Employee profile not found."}, status=400)

        ticket = get_object_or_404(SupportTicket, id=ticket_id)

        # Only admins or managers or HR or global support agent can assign tickets
        is_support_staff = (
            request.user.role in ["COMPANY_ADMIN", "SUPERADMIN", "MANAGER", "EMPLOYEE_MANAGER"]
            or employee.is_support_agent
        )
        if not is_support_staff:
            return JsonResponse({"status": "error", "message": "Access denied."}, status=403)

        # Verify company match or global support clearance
        if ticket.employee.company != employee.company and not employee.is_support_agent:
            return JsonResponse({"status": "error", "message": "Access denied."}, status=403)

        agent_id = request.POST.get("agent_id")
        if agent_id:
            agent = get_object_or_404(Employee, id=agent_id)
            ticket.assigned_to = agent
            ticket.save()

            # Auto comment about assignment
            TicketMessage.objects.create(
                ticket=ticket, sender=employee, message=f"👤 Ticket assigned to *{agent.user.get_full_name()}*"
            )

            return JsonResponse({"status": "success", "assigned_name": agent.user.get_full_name()})
        else:
            ticket.assigned_to = None
            ticket.save()

            # Auto comment about assignment removal
            TicketMessage.objects.create(ticket=ticket, sender=employee, message="👤 Ticket unassigned")

            return JsonResponse({"status": "success", "assigned_name": "Unassigned"})

    return JsonResponse({"status": "error", "message": "POST request expected."}, status=405)
