import calendar
from datetime import date

from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from companies.models import Company
from core.email_utils import send_payslip_email
from core.utils import save_pdf_to_model
from employees.models import Employee, Payslip
from employees.payroll_utils import calculate_payslip_breakdown, num2words_flexible

from .decorators import finance_manager_required
from .models import FinanceAuditLog, PayrollBatch


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")
    return ip


@finance_manager_required
def dashboard(request):
    """Centralized Finance Portal Dashboard for cross-company payroll"""
    companies = Company.objects.filter(is_active=True).order_by("name")

    today = date.today()
    selected_month = int(request.GET.get("month", today.month))
    selected_year = int(request.GET.get("year", today.year))
    selected_company_id = request.GET.get("company", "all")

    # Month range calculation
    num_days = calendar.monthrange(selected_year, selected_month)[1]
    month_start = date(selected_year, selected_month, 1)
    month_end = date(selected_year, selected_month, num_days)

    # Base query for employees who were employed during the selected month
    employees = Employee.objects.filter(Q(date_of_joining__isnull=True) | Q(date_of_joining__lte=month_end)).filter(
        Q(is_active=True) | Q(employment_status="ACTIVE") | (Q(exit_date__isnull=False) & Q(exit_date__gte=month_start))
    )

    if selected_company_id and selected_company_id != "all":
        employees = employees.filter(company_id=selected_company_id)

    employees = employees.select_related("user", "company", "location").order_by(
        Lower("company__name"), Lower("user__first_name"), Lower("user__last_name")
    )

    # Get payslips for selected month/year
    existing_payslips = Payslip.objects.filter(month__month=selected_month, month__year=selected_year)
    if selected_company_id and selected_company_id != "all":
        existing_payslips = existing_payslips.filter(employee__company_id=selected_company_id)

    payslip_map = {slip.employee_id: slip for slip in existing_payslips}

    # Package employee details with payslips
    employee_data = []
    calculated_count = 0
    for emp in employees:
        slip = payslip_map.get(emp.id)
        if slip:
            calculated_count += 1
        employee_data.append({"employee": emp, "payslip": slip})

    months = [{"value": i, "name": calendar.month_name[i]} for i in range(1, 13)]
    years = range(today.year - 2, today.year + 2)

    # Fetch recent payroll batches
    batches = PayrollBatch.objects.all().prefetch_related("companies")[:10]
    audit_logs = FinanceAuditLog.objects.all().select_related("user", "company")[:15]

    context = {
        "title": "Centralized Finance Portal",
        "companies": companies,
        "employee_data": employee_data,
        "calculated_count": calculated_count,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "selected_company_id": selected_company_id,
        "months": months,
        "years": years,
        "batches": batches,
        "audit_logs": audit_logs,
    }
    return render(request, "finance_portal/dashboard.html", context)


def generate_payslip_internal(employee, month, year, worked_days=None, monthly_gross=None):
    """
    Core payroll generation helper (mirroring core/views.py process_payslip_generation).
    Calculates breakdown, saves Payslip, and renders PDF.
    """
    total_days = calendar.monthrange(year, month)[1]
    month_date = date(year, month, 1)

    if worked_days is None:
        worked_days = float(total_days)

    # If custom monthly gross is supplied (e.g. from Excel upload), use it to calculate annual CTC
    annual_ctc = float(monthly_gross) * 12 if monthly_gross is not None else float(employee.annual_ctc or 0.0)

    # Calculate breakdown
    breakdown = calculate_payslip_breakdown(
        annual_ctc,
        worked_days,
        total_days,
        employee.pf_enabled,
        location=employee.location,
        company=employee.company,
        month=month,
        year=year,
    )

    payslip, created = Payslip.objects.get_or_create(employee=employee, month=month_date)

    # Set payslip fields
    payslip.basic = breakdown["basic"]
    payslip.hra = breakdown["hra"]
    payslip.lta = breakdown["lta"]
    payslip.other_allowance = breakdown["other_allowance"]

    # Map location specific allowances
    if breakdown.get("country_code", "IN") == "IN":
        payslip.conveyance_allowance = breakdown.get("lta", 0.0)
        payslip.special_allowance = breakdown.get("other_allowance", 0.0)
    else:
        payslip.conveyance_allowance = breakdown.get("conveyance", 0.0)
        payslip.special_allowance = breakdown.get("medical", 0.0)

    payslip.monthly_gross = breakdown["full_monthly_gross"]
    payslip.gross_salary = breakdown["gross_monthly"]
    payslip.employee_pf = breakdown["employee_pf"]
    payslip.employer_pf = breakdown["employer_pf"]
    payslip.professional_tax = breakdown["professional_tax"]
    payslip.net_salary = breakdown["net_salary"]
    payslip.worked_days = worked_days
    payslip.total_days = breakdown.get("display_days", total_days)
    payslip.save()

    # Generate branding and currency details for PDF context
    currency = "INR"
    currency_name = "Rupees"
    if employee.location:
        currency = employee.location.currency or "INR"
        if employee.location.country_code == "IN" or currency == "INR":
            currency_name = "Rupees"
        elif employee.location.country_code == "BD" or currency == "BDT":
            currency_name = "Taka"
        elif employee.location.country_code == "US" or currency == "USD":
            currency_name = "Dollars"
        else:
            currency_name = currency

    cname_upper = employee.company.name.upper()
    branding = {
        "name": "PETABYTZ TECHNOLOGY SERVICES PVT LTD",
        "address": "PLOT NO 201 & 202, 1ST FLOOR, DMR CORPORATE, KAVURI HILLS RD, HYDERABAD, TELANGANA 500081.",
    }
    if "SOFTSTANDARD" in cname_upper or "RMINDS" in cname_upper:
        branding["name"] = "SOFTSTANDARD SOLUTIONS"

    if employee.location and employee.location.address_line1:
        loc = employee.location
        addr = f"{loc.address_line1}"
        if loc.address_line2:
            addr += f", {loc.address_line2}"
        addr += f", {loc.city}"
        if loc.state:
            addr += f", {loc.state}"
        if loc.postal_code:
            addr += f" {loc.postal_code}"
        branding["address"] = addr

    context = {
        "payslip": payslip,
        "company": employee.company,
        "branding": branding,
        "net_salary_words": num2words_flexible(round(payslip.net_salary or 0), currency_name),
        "currency": currency,
        "basic_rounded": round(payslip.basic or 0),
        "hra_rounded": round(payslip.hra or 0),
        "conveyance_rounded": round(payslip.conveyance_allowance or 0),
        "special_rounded": round(payslip.special_allowance or 0),
        "employer_pf_rounded": round(payslip.employer_pf or 0),
        "employee_pf_rounded": round(payslip.employee_pf or 0),
        "professional_tax_rounded": round(payslip.professional_tax or 0),
        "total_earnings_ctc": round((payslip.gross_salary or 0) + (payslip.employer_pf or 0)),
        "total_contributions": round((payslip.employee_pf or 0) + (payslip.employer_pf or 0)),
        "net_salary_rounded": round(payslip.net_salary or 0),
        "payable_units": f"{breakdown.get('display_days', total_days)} Days",
    }

    filename = f"payslip_{employee.badge_id}_{month_date.strftime('%b_%Y')}.pdf"
    save_pdf_to_model(payslip, "employees/payslip_pdf.html", context, filename)
    return payslip


@finance_manager_required
def process_bulk_payroll(request):
    """Process bulk payroll for a company or all companies"""
    if request.method != "POST":
        return redirect("finance_portal:dashboard")

    company_id = request.POST.get("company_id", "all")
    month = int(request.POST.get("month"))
    year = int(request.POST.get("year"))
    auto_send_email = request.POST.get("auto_send_email") == "on"

    # Calculate range
    num_days = calendar.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, num_days)

    # Filter employees
    employees = Employee.objects.filter(Q(date_of_joining__isnull=True) | Q(date_of_joining__lte=month_end)).filter(
        Q(is_active=True) | Q(employment_status="ACTIVE") | (Q(exit_date__isnull=False) & Q(exit_date__gte=month_start))
    )

    # Apply company filter
    target_companies = Company.objects.filter(is_active=True)
    if company_id and company_id != "all":
        employees = employees.filter(company_id=company_id)
        target_companies = target_companies.filter(id=company_id)

    if not employees.exists():
        messages.error(request, "No eligible employees found for the selected company/companies.")
        return redirect(f"/finance/?company={company_id}&month={month}&year={year}")

    # Create the Batch record
    batch = PayrollBatch.objects.create(
        month=month,
        year=year,
        status="PROCESSING",
        total_employees=employees.count(),
        processed_employees=0,
        total_amount=0.0,
        created_by=request.user,
    )
    batch.companies.add(*target_companies)

    processed_count = 0
    total_amount = 0.0
    errors = []

    for emp in employees:
        try:
            # Generate payslip
            payslip = generate_payslip_internal(emp, month, year)

            # Send email if requested
            if auto_send_email:
                send_payslip_email(payslip)

            processed_count += 1
            if payslip.net_salary:
                total_amount += float(payslip.net_salary)

            # Update batch progress
            batch.processed_employees = processed_count
            batch.total_amount = total_amount
            batch.save()

        except Exception as e:
            errors.append(f"Error for {emp.user.get_full_name()}: {str(e)}")

    # Finalize batch
    if errors and processed_count == 0:
        batch.status = "FAILED"
    else:
        batch.status = "COMPLETED"
    batch.save()

    # Audit log
    company_log = None if company_id == "all" else target_companies.first()
    comp_name_str = "All Companies" if company_id == "all" else target_companies.first().name
    details = f"Processed bulk payroll for {comp_name_str}. Period: {month}/{year}. Total Employees: {batch.total_employees}, Processed: {processed_count}, Net Payroll: {total_amount:.2f}."
    if errors:
        details += f" Errors encountered: {len(errors)}"

    FinanceAuditLog.objects.create(
        user=request.user,
        action="BULK_PAYROLL_PROCESS",
        company=company_log,
        details=details,
        ip_address=get_client_ip(request),
    )

    if errors:
        messages.warning(
            request, f"Payroll batch processed with some errors ({len(errors)} failed out of {batch.total_employees})."
        )
    else:
        messages.success(request, f"Successfully processed payroll batch for {processed_count} employees!")

    return redirect(f"/finance/?company={company_id}&month={month}&year={year}")


@finance_manager_required
def send_single_payslip_email_view(request, payslip_id):
    """View to email a single generated payslip manually from the dashboard"""
    payslip = get_object_or_404(Payslip, id=payslip_id)
    if not payslip.pdf_file:
        # Generate the PDF if it's missing for some reason
        try:
            generate_payslip_internal(payslip.employee, payslip.month.month, payslip.month.year)
            payslip.refresh_from_db()
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Could not generate PDF: {str(e)}"}, status=500)

    success = send_payslip_email(payslip)

    # Audit log
    FinanceAuditLog.objects.create(
        user=request.user,
        action="SEND_SINGLE_PAYSLIP",
        company=payslip.employee.company,
        details=f"Emailed payslip to {payslip.employee.user.get_full_name()} for {payslip.month.strftime('%B %Y')}.",
        ip_address=get_client_ip(request),
    )

    if success:
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax"):
            return JsonResponse({"status": "success", "message": "Email sent successfully!"})
        messages.success(request, f"Payslip successfully emailed to {payslip.employee.user.get_full_name()}!")
    else:
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax"):
            return JsonResponse({"status": "error", "message": "Failed to send email. Check logs."}, status=500)
        messages.error(
            request, f"Failed to send email to {payslip.employee.user.get_full_name()}. Please check configuration."
        )

    return redirect(
        f"/finance/?company={payslip.employee.company.id}&month={payslip.month.month}&year={payslip.month.year}"
    )


@finance_manager_required
def process_bulk_excel_upload(request):
    """
    Process cross-company or single-company payroll via Excel upload.
    Matches active employees by badge number, calculates breakdown,
    saves PDF payslips, and optionally dispatches payslips to user emails immediately.
    """
    if request.method != "POST":
        return redirect("finance_portal:dashboard")

    import openpyxl

    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        messages.error(request, "Please upload a valid Excel file.")
        return redirect("finance_portal:dashboard")

    company_id = request.POST.get("company_id", "all")
    month = int(request.POST.get("month", date.today().month))
    year = int(request.POST.get("year", date.today().year))
    auto_send_email = request.POST.get("auto_send_email") == "on"

    try:
        wb = openpyxl.load_workbook(excel_file)
        ws = wb.active

        # Extract headers mapping from Row 2 or Row 1
        header_map = {}
        header_row = list(ws.iter_rows(min_row=2, max_row=2, values_only=True))[0]
        if not header_row or not any(header_row):
            header_row = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))[0]
            start_row = 2
        else:
            start_row = 3

        for idx, value in enumerate(header_row):
            if value:
                header_map[str(value).strip().lower()] = idx

        # Support flexible / alternative names for matching columns
        badge_key = None
        gross_key = None
        days_key = None

        for key in header_map:
            if any(term in key for term in ["employee", "badge", "id", "number", "emp"]):
                badge_key = key
            if any(term in key for term in ["gross", "amount", "salary", "ctc", "earned"]):
                gross_key = key
            if any(term in key for term in ["day", "hour", "unit", "payable", "worked"]):
                days_key = key

        # Fill standard defaults if not matched
        if not badge_key:
            badge_key = "employee number"
        if not gross_key:
            gross_key = "monthly earned gross"
        if not days_key:
            days_key = "no of payable units (days / hours / units)"

        # Validate critical headers exist
        missing = []
        for col in [badge_key, gross_key]:
            if col not in header_map:
                missing.append(col)
        if missing:
            messages.error(
                request,
                "Could not find required columns in your file. Ensure headers for employee number/badge ID and gross salary are present.",
            )
            return redirect("finance_portal:dashboard")

        success_count = 0
        error_count = 0

        # Initialize PayrollBatch
        batch = PayrollBatch.objects.create(
            month=month,
            year=year,
            total_employees=0,
            processed_employees=0,
            total_amount=0.0,
            status="PROCESSING",
            created_by=request.user,
        )
        selected_company = None
        if company_id != "all":
            selected_company = Company.objects.get(id=company_id)
            batch.companies.add(selected_company)

        for row in ws.iter_rows(min_row=start_row, values_only=True):
            if len(row) <= max(header_map[badge_key], header_map[gross_key]):
                continue

            badge_val = row[header_map[badge_key]]
            if badge_val is None:
                continue

            badge_id = str(badge_val).strip()
            gross_val = row[header_map[gross_key]]
            days_val = row[header_map[days_key]] if days_key in header_map else None

            if gross_val is None:
                continue

            try:
                # Query active employee matching the Badge ID
                emp_query = Employee.objects.filter(badge_id=badge_id, is_active=True)
                if company_id != "all":
                    emp_query = emp_query.filter(company_id=company_id)
                employee = emp_query.first()

                if not employee:
                    error_count += 1
                    continue

                monthly_gross = float(gross_val)
                worked_days = float(days_val) if days_val is not None else None

                # Perform the full payslip generation cycle
                payslip = generate_payslip_internal(
                    employee=employee, month=month, year=year, worked_days=worked_days, monthly_gross=monthly_gross
                )

                # Email automatically with dynamic name and branding
                if auto_send_email:
                    send_payslip_email(payslip)

                success_count += 1
                batch.total_amount += float(payslip.net_salary or 0.0)

            except Exception:
                import traceback

                traceback.print_exc()
                error_count += 1

        # Conclude batch state
        batch.total_employees = success_count + error_count
        batch.processed_employees = success_count
        batch.status = "COMPLETED" if success_count > 0 else "FAILED"
        batch.save()

        # Log to FinanceAuditLog
        FinanceAuditLog.objects.create(
            user=request.user,
            company=selected_company,
            action="EXCEL_BULK_PAYROLL",
            ip_address=get_client_ip(request),
            details=f"Processed Excel bulk upload. Calculated and processed: {success_count}, Errors/Mismatches: {error_count}. Batch ID: {batch.batch_id}.",
        )

        messages.success(
            request,
            f"Successfully processed {success_count} payslips from Excel. {error_count} records failed or had no matching active employee.",
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        messages.error(request, f"Failed to read or parse Excel file: {str(e)}")

    return redirect(f"/finance/?company={company_id}&month={month}&year={year}")
