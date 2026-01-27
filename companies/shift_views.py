from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.forms import inlineformset_factory
from companies.models import ShiftSchedule, ShiftBreak
from companies.forms import ShiftScheduleForm, ShiftBreakForm
from accounts.models import User


@login_required
def shift_list(request):
    """List all shifts for the company"""
    if not (request.user.role == User.Role.COMPANY_ADMIN or request.user.is_superuser):
        messages.error(request, "Only admins can manage shifts.")
        return redirect("dashboard")

    shifts = (
        ShiftSchedule.objects.filter(company=request.user.company)
        .prefetch_related("breaks")
        .order_by("name")
    )
    return render(request, "companies/shift_list.html", {"shifts": shifts})


@login_required
def shift_create(request):
    """Create a new shift with breaks"""
    if not (request.user.role == User.Role.COMPANY_ADMIN or request.user.is_superuser):
        messages.error(request, "Only admins can create shifts.")
        return redirect("dashboard")

    ShiftBreakFormSet = inlineformset_factory(
        ShiftSchedule, ShiftBreak, form=ShiftBreakForm, extra=1, can_delete=True
    )

    if request.method == "POST":
        form = ShiftScheduleForm(request.POST)
        break_formset = ShiftBreakFormSet(request.POST)

        if form.is_valid() and break_formset.is_valid():
            shift = form.save(commit=False)
            shift.company = request.user.company
            shift.save()

            # Save breaks
            break_formset.instance = shift
            break_formset.save()

            messages.success(request, f'Shift "{shift.name}" created successfully!')
            return redirect("shift_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ShiftScheduleForm()
        break_formset = ShiftBreakFormSet()

    return render(
        request,
        "companies/shift_form.html",
        {"form": form, "break_formset": break_formset, "action": "Create"},
    )


@login_required
def shift_edit(request, pk):
    """Edit an existing shift and its breaks"""
    if not (request.user.role == User.Role.COMPANY_ADMIN or request.user.is_superuser):
        messages.error(request, "Only admins can edit shifts.")
        return redirect("dashboard")

    shift = get_object_or_404(ShiftSchedule, pk=pk, company=request.user.company)

    ShiftBreakFormSet = inlineformset_factory(
        ShiftSchedule, ShiftBreak, form=ShiftBreakForm, extra=0, can_delete=True
    )

    if request.method == "POST":
        form = ShiftScheduleForm(request.POST, instance=shift)
        break_formset = ShiftBreakFormSet(request.POST, instance=shift)

        if form.is_valid() and break_formset.is_valid():
            form.save()
            break_formset.save()

            messages.success(request, f'Shift "{shift.name}" updated successfully!')
            return redirect("shift_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ShiftScheduleForm(instance=shift)
        break_formset = ShiftBreakFormSet(instance=shift)

    return render(
        request,
        "companies/shift_form.html",
        {"form": form, "break_formset": break_formset, "action": "Edit"},
    )


@login_required
def shift_delete(request, pk):
    """Delete a shift"""
    if not (request.user.role == User.Role.COMPANY_ADMIN or request.user.is_superuser):
        messages.error(request, "Only admins can delete shifts.")
        return redirect("dashboard")

    shift = get_object_or_404(ShiftSchedule, pk=pk, company=request.user.company)

    if request.method == "POST":
        shift_name = shift.name
        shift.delete()
        messages.success(request, f'Shift "{shift_name}" deleted successfully!')
        return redirect("shift_list")

    return render(request, "companies/shift_confirm_delete.html", {"shift": shift})
