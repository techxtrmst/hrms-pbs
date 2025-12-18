from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from employees.models import Attendance, Employee, LeaveBalance, LeaveRequest, Payslip, HandbookSection, PolicySection
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Count, Q
import calendar
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import datetime, date
from datetime import timedelta

@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html')

@login_required
def personal_home(request):
    context = {}
    if hasattr(request.user, 'employee_profile'):
        employee = request.user.employee_profile
        today = timezone.localdate()
        
        # Today's attendance
        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        context['attendance'] = attendance
        
        # Stats (Last 7 days)
        last_week = today - timedelta(days=7)
        recent_attendance = Attendance.objects.filter(employee=employee, date__gte=last_week)
        
        total_seconds = 0
        count = 0
        for att in recent_attendance:
            if att.clock_in and att.clock_out:
                total_seconds += (att.clock_out - att.clock_in).total_seconds()
                count += 1
        
        avg_hours = "00:00"
        if count > 0:
            avg_sec = total_seconds / count
            h = int(avg_sec // 3600)
            m = int((avg_sec % 3600) // 60)
            avg_hours = f"{h:02d}:{m:02d}"
        
        context['avg_hours'] = avg_hours
        context['on_time_percentage'] = "100%" # Stub for now
        
        # Attendance History
        history = Attendance.objects.filter(employee=employee).order_by('-date')[:30]
        context['attendance_history'] = history
        
    return render(request, 'core/personal_home.html', context)

# --- Me Section Stubs ---
@login_required
def my_profile(request):
    return render(request, 'employees/stub.html', {'title': 'My Profile'}) # Should actually redirect to employee_profile or render it


@login_required
def my_leaves(request):
    try:
        employee = request.user.employee_profile
    except Exception:
        # Graceful fallback or auto-create (reusing logic from profile view might be better)
        messages.error(request, "Employee profile not found.")
        return redirect('personal_home')

    # Get or create balance (accrual handled by command, but ensure existence)
    balance, created = LeaveBalance.objects.get_or_create(employee=employee)

    if request.method == 'POST':
        leave_type = request.POST.get('leave_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason')

        # Basic Validation
        if leave_type and start_date and end_date:
            try:
                # Todo: Add overlap validation and balance check
                LeaveRequest.objects.create(
                    employee=employee,
                    leave_type=leave_type,
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason
                )
                messages.success(request, "Leave request submitted successfully.")
            except Exception as e:
                messages.error(request, f"Error submitting request: {e}")
        else:
            messages.error(request, "All fields are required.")
        return redirect('my_leaves')

    recent_requests = LeaveRequest.objects.filter(employee=employee).order_by('-created_at')[:5]

    return render(request, 'employees/leave_dashboard.html', {
        'title': 'My Leaves',
        'balance': balance,
        'recent_requests': recent_requests
    })

@login_required
def my_finance(request):
    try:
        employee = request.user.employee_profile
    except Exception:
        messages.error(request, "Employee profile not found.")
        return redirect('personal_home')
        
    payslips = Payslip.objects.filter(employee=employee).order_by('-month')
    
    return render(request, 'employees/finance_dashboard.html', {
        'title': 'My Finance',
        'employee': employee,
        'payslips': payslips
    })

@login_required
def handbook(request):
    try:
        # Auto-initialize default sections if empty (for demo)
        if not HandbookSection.objects.exists():
            HandbookSection.objects.create(title="Company Rules", order=1, content="<h4>Working Hours</h4><p>Standard working hours are 9:00 AM to 6:00 PM.</p>")
            HandbookSection.objects.create(title="Conduct", order=2, content="<h4>Code of Conduct</h4><p>Employees are expected to maintain professionalism.</p>")
            
        sections = HandbookSection.objects.filter(is_active=True)
        return render(request, 'core/handbook.html', {
            'title': 'Employee Handbook',
            'sections': sections
        })
    except Exception as e:
        messages.error(request, f"Error loading handbook: {e}")
        return redirect('personal_home')

@login_required
def policy(request):
    try:
        # Auto-initialize default sections if empty
        if not PolicySection.objects.exists():
            PolicySection.objects.create(title="Leave Policy", order=1, content="<h4>Annual Leave</h4><p>Employees are entitled to 25 days of annual leave.</p>")
            PolicySection.objects.create(title="HR Policy", order=2, content="<h4>Recruitment</h4><p>We are an equal opportunity employer.</p>")

        sections = PolicySection.objects.filter(is_active=True)
        return render(request, 'core/policy.html', {
            'title': 'Company Policy',
            'sections': sections
        })
    except Exception as e:
         messages.error(request, f"Error loading policy: {e}")
         return redirect('personal_home')

# --- Employees Section Stubs ---
@login_required
def org_chart(request):
    # Ensure user has a company
    if not hasattr(request.user, 'company') or not request.user.company:
         messages.error(request, "You are not linked to any company.")
         return redirect('dashboard')

    # Fetch all employees for this company
    employees = Employee.objects.filter(company=request.user.company).select_related('user', 'manager')
    
    # Build a dictionary of employees by ID for O(1) access
    emp_map = {emp.id: emp for emp in employees}
    
    # Build the tree structure
    # nodes = { emp_id: {'employee': emp, 'direct_reports': []} }
    nodes = {}
    for emp in employees:
        nodes[emp.id] = {'employee': emp, 'direct_reports': []}
    
    roots = []
    
    for emp in employees:
        if emp.manager_id and emp.manager_id in nodes:
            # Add to manager's direct reports
            nodes[emp.manager_id]['direct_reports'].append(nodes[emp.id])
        else:
            # No manager (or manager not in this list/company), so this is a root node
            roots.append(nodes[emp.id])
            
    return render(request, 'core/org_chart.html', {
        'title': 'Organisation Chart',
        'roots': roots,
        'company': request.user.company
    })

@login_required
def attendance_analytics(request):
    if not hasattr(request.user, 'company') or not request.user.company:
         messages.error(request, "Restricted access.")
         return redirect('dashboard')
    
    today = timezone.localtime().date()
    
    # Base query for company employees
    employees = Employee.objects.filter(company=request.user.company)
    total_employees = employees.count()
    
    # Today's stats
    attendance_today = Attendance.objects.filter(employee__company=request.user.company, date=today)
    
    present_today = attendance_today.filter(status='PRESENT').count()
    absent_today = attendance_today.filter(status='ABSENT').count()
    leave_today = attendance_today.filter(status='LEAVE').count()
    wfh_today = attendance_today.filter(status='WFH').count()
    on_duty_today = attendance_today.filter(status='ON_DUTY').count()
    
    # Calculate percentages
    present_pct = (present_today / total_employees * 100) if total_employees > 0 else 0
    
    return render(request, 'core/attendance_analytics.html', {
        'title': 'Attendance Analytics',
        'total_employees': total_employees,
        'present_today': present_today,
        'absent_today': absent_today,
        'leave_today': leave_today,
        'wfh_today': wfh_today,
        'on_duty_today': on_duty_today,
        'present_pct': round(present_pct, 1),
    })

@login_required
def attendance_report(request):
    if not hasattr(request.user, 'company') or not request.user.company:
         messages.error(request, "Restricted access.")
         return redirect('dashboard')
         
    today = timezone.localtime().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    num_days = calendar.monthrange(year, month)[1]
    days_range = range(1, num_days + 1)
    
    employees = Employee.objects.filter(company=request.user.company).select_related('user', 'manager')
    attendances = Attendance.objects.filter(
        employee__company=request.user.company, 
        date__year=year, 
        date__month=month
    )
    
    att_map = {}
    for att in attendances:
        if att.employee_id not in att_map:
            att_map[att.employee_id] = {}
        att_map[att.employee_id][att.date.day] = att

    reports = []
    
    for emp in employees:
        emp_data = {'employee': emp, 'days': [], 'stats': {
            'present': 0, 'absent': 0, 'leave': 0, 'wfh': 0
        }}
        
        for day in days_range:
            att = att_map.get(emp.id, {}).get(day)
            status_code = att.status if att else "-"
            display_val = "-"
            
            if status_code == 'PRESENT': 
                display_val = 'P'
                emp_data['stats']['present'] += 1
            elif status_code == 'ABSENT': 
                display_val = 'A'
                emp_data['stats']['absent'] += 1
            elif status_code == 'LEAVE': 
                display_val = 'L'
                emp_data['stats']['leave'] += 1
            elif status_code == 'WFH':
                display_val = 'WFH'
                emp_data['stats']['wfh'] += 1
                
            emp_data['days'].append(display_val)
        
        reports.append(emp_data)
        
    return render(request, 'core/attendance_report.html', {
        'title': 'Attendance Detailed Report',
        'reports': reports,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'days_range': days_range,
        'num_days': num_days
    })

@login_required
def download_attendance(request):
    if not hasattr(request.user, 'company') or not request.user.company:
         return HttpResponse("Unauthorized", status=403)

    # Defaults to current month
    today = timezone.localtime().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # File name
    filename = f"Attendance_Report_{month}_{year}.xlsx"
    
    # Create Workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{calendar.month_name[month]} {year}"
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2c5282", end_color="2c5282", fill_type="solid")
    
    # 1. Define Headers
    # Static Headers
    headers = [
        "Employee Number", "Employee Name", "Job Title", "Department", 
        "Location", "Reporting Manager"
    ]
    
    # Dynamic Date Headers
    num_days = calendar.monthrange(year, month)[1]
    date_cols = []
    for day in range(1, num_days + 1):
        date_obj = date(year, month, day)
        col_name = date_obj.strftime("%d-%b") # 01-Dec
        headers.append(col_name)
        date_cols.append(date_obj)
        
    # Summary Headers
    summary_headers = [
        "Total Days", "WFH", "Pending WFH", "On Duty", "Pending On Duty", 
        "WOH", "Weekly Offs", "Holidays", "Absent Days", "Present Days", 
        "Late Arrival Days", "Penalized Paid Leave", "Paid Leave Taken", 
        "Pending Paid Leave Taken", "Total Paid Leave", "Penalized Unpaid Leave", 
        "Unpaid Leave Taken", "Pending Unpaid Leave Taken", "Total Unpaid Leave"
    ]
    headers.extend(summary_headers)
    
    # Write Headers
    for col_num, header_title in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header_title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        
    # 2. Fetch Data
    employees = Employee.objects.filter(company=request.user.company).select_related('user', 'manager')
    attendances = Attendance.objects.filter(
        employee__company=request.user.company, 
        date__year=year, 
        date__month=month
    )
    
    # Map attendance by employee and date
    # att_map[emp_id][day_int] = attendance_obj
    att_map = {}
    for att in attendances:
        if att.employee_id not in att_map:
            att_map[att.employee_id] = {}
        att_map[att.employee_id][att.date.day] = att
        
    # 3. Write Rows
    row_num = 2
    for emp in employees:
        # Basic Info
        ws.cell(row=row_num, column=1, value=emp.badge_id)
        ws.cell(row=row_num, column=2, value=emp.user.get_full_name())
        ws.cell(row=row_num, column=3, value=emp.designation)
        ws.cell(row=row_num, column=4, value=emp.department)
        ws.cell(row=row_num, column=5, value="Office") # Placeholder for Location
        ws.cell(row=row_num, column=6, value=emp.manager.user.get_full_name() if emp.manager else "-")
        
        # Stats Counters
        stats = {
            'present': 0, 'absent': 0, 'leave': 0, 'wfh': 0, 'on_duty': 0,
            'weekly_off': 0, 'holiday': 0
        }
        
        # Date Columns
        col_idx = 7
        for day in range(1, num_days + 1):
            att = att_map.get(emp.id, {}).get(day)
            status_code = att.status if att else "-"
            
            # Simple mapping for display
            display_val = status_code
            if status_code == 'PRESENT': display_val = 'P'; stats['present'] += 1
            elif status_code == 'ABSENT': display_val = 'A'; stats['absent'] += 1
            elif status_code == 'LEAVE': display_val = 'L'; stats['leave'] += 1
            elif status_code == 'WFH': display_val = 'WFH'; stats['wfh'] += 1
            elif status_code == 'ON_DUTY': display_val = 'OD'; stats['on_duty'] += 1
            elif status_code == 'WEEKLY_OFF': display_val = 'WO'; stats['weekly_off'] += 1
            elif status_code == 'HOLIDAY': display_val = 'H'; stats['holiday'] += 1
            
            cell = ws.cell(row=row_num, column=col_idx, value=display_val)
            cell.alignment = Alignment(horizontal='center')
            col_idx += 1
            
        # Summary Columns (Approximation based on available data)
        # "Total Days", "WFH", "Pending WFH", "On Duty", "Pending On Duty", ...
        
        ws.cell(row=row_num, column=col_idx, value=num_days); col_idx+=1 # Total Days
        ws.cell(row=row_num, column=col_idx, value=stats['wfh']); col_idx+=1 # WFH
        ws.cell(row=row_num, column=col_idx, value=0); col_idx+=1 # Pending WFH
        ws.cell(row=row_num, column=col_idx, value=stats['on_duty']); col_idx+=1 # On Duty
        ws.cell(row=row_num, column=col_idx, value=0); col_idx+=1 # Pending OD
        ws.cell(row=row_num, column=col_idx, value=0); col_idx+=1 # WOH
        ws.cell(row=row_num, column=col_idx, value=stats['weekly_off']); col_idx+=1 # Weekly Offs
        ws.cell(row=row_num, column=col_idx, value=stats['holiday']); col_idx+=1 # Holidays
        ws.cell(row=row_num, column=col_idx, value=stats['absent']); col_idx+=1 # Absent
        ws.cell(row=row_num, column=col_idx, value=stats['present']); col_idx+=1 # Present
        ws.cell(row=row_num, column=col_idx, value=0); col_idx+=1 # Late Arrival (Need logic)
        
        # Leaves (Simplified)
        ws.cell(row=row_num, column=col_idx, value=0); col_idx+=1 # Penalized Paid
        ws.cell(row=row_num, column=col_idx, value=stats['leave']); col_idx+=1 # Paid Taken (Assuming CL/SL)
        ws.cell(row=row_num, column=col_idx, value=0); col_idx+=1 # Pending Paid
        ws.cell(row=row_num, column=col_idx, value=stats['leave']); col_idx+=1 # Total Paid
        
        ws.cell(row=row_num, column=col_idx, value=0); col_idx+=1 # Penalized Unpaid
        ws.cell(row=row_num, column=col_idx, value=0); col_idx+=1 # Unpaid Taken
        ws.cell(row=row_num, column=col_idx, value=0); col_idx+=1 # Pending Unpaid
        ws.cell(row=row_num, column=col_idx, value=0); col_idx+=1 # Total Unpaid
        
        row_num += 1

    # Return Excel File
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

# --- Leaves Section Stubs ---
@login_required
def leave_requests(request):
    return render(request, 'core/stub.html', {'title': 'Leave Requests'})

@login_required
def leave_history(request):
    return render(request, 'core/stub.html', {'title': 'Leave History'})

# --- Payroll Section Stubs ---
@login_required
def payroll_dashboard(request):
    return render(request, 'core/stub.html', {'title': 'Payroll Dashboard'})

# --- Configuration Section Stubs ---
@login_required
def holidays(request):
    return render(request, 'core/stub.html', {'title': 'Holiday Configuration'})

@login_required
def company_leaves(request):
    return render(request, 'core/stub.html', {'title': 'Company Leave Configuration'})
