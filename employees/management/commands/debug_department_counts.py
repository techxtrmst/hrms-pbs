"""
Management command to debug and verify department employee counts
Run this on deployed server to check actual data and fix any issues
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Employee, Attendance
from collections import Counter
from django.db.models import Count, Q


class Command(BaseCommand):
    help = 'Debug department employee counts and verify admin dashboard logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-data',
            action='store_true',
            help='Fix common data issues (trim whitespace, etc.)'
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Filter by specific company ID'
        )

    def handle(self, *args, **options):
        fix_data = options['fix_data']
        company_id = options.get('company_id')
        
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("  DEPARTMENT EMPLOYEE COUNT DEBUG REPORT"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        
        # Filter employees
        employees = Employee.objects.all()
        if company_id:
            employees = employees.filter(company_id=company_id)
            self.stdout.write(f"\n🏢 Filtering by Company ID: {company_id}")
        
        # Show active vs inactive breakdown
        total_employees = employees.count()
        active_employees = employees.filter(is_active=True)
        inactive_employees = employees.filter(is_active=False)
        
        self.stdout.write(f"\n📊 EMPLOYEE OVERVIEW:")
        self.stdout.write(f"  Total Employees: {total_employees}")
        self.stdout.write(f"  Active Employees: {active_employees.count()}")
        self.stdout.write(f"  Inactive Employees: {inactive_employees.count()}")
        
        # Focus on active employees (what dashboard uses)
        employees = active_employees
        
        # 1. Raw department data analysis
        self.stdout.write(f"\n" + "=" * 80)
        self.stdout.write("1. RAW DEPARTMENT DATA ANALYSIS")
        self.stdout.write("=" * 80)
        
        dept_list = list(employees.values_list('department', flat=True))
        dept_counts = Counter(dept_list)
        
        self.stdout.write(f"\nTotal active employees: {len(dept_list)}")
        self.stdout.write(f"Departments found: {len(dept_counts)}")
        
        # Show all departments with counts
        self.stdout.write(f"\nDepartment breakdown:")
        for dept, count in sorted(dept_counts.items()):
            if dept is None:
                self.stdout.write(f"  [NULL/Empty]: {count} employees")
            elif dept.strip() != dept:
                self.stdout.write(f"  '{dept}' (has whitespace): {count} employees")
            else:
                self.stdout.write(f"  {dept}: {count} employees")
        
        # 2. Check for data quality issues
        self.stdout.write(f"\n" + "=" * 80)
        self.stdout.write("2. DATA QUALITY ISSUES")
        self.stdout.write("=" * 80)
        
        issues_found = False
        
        # Check for null/empty departments
        null_dept_count = employees.filter(Q(department__isnull=True) | Q(department='')).count()
        if null_dept_count > 0:
            issues_found = True
            self.stdout.write(f"⚠️  {null_dept_count} employees have NULL/empty department")
        
        # Check for whitespace issues
        whitespace_issues = []
        for dept in dept_counts.keys():
            if dept and dept.strip() != dept:
                whitespace_issues.append(dept)
        
        if whitespace_issues:
            issues_found = True
            self.stdout.write(f"⚠️  Departments with whitespace issues:")
            for dept in whitespace_issues:
                self.stdout.write(f"     '{dept}' -> '{dept.strip()}'")
        
        # Check for similar department names
        dept_names = [d.strip().lower() for d in dept_counts.keys() if d and d.strip()]
        similar_depts = {}
        for dept in dept_counts.keys():
            if dept and dept.strip():
                normalized = dept.strip().lower()
                if normalized not in similar_depts:
                    similar_depts[normalized] = []
                similar_depts[normalized].append(dept)
        
        similar_found = False
        for normalized, variations in similar_depts.items():
            if len(variations) > 1:
                similar_found = True
                if not issues_found:
                    issues_found = True
                self.stdout.write(f"⚠️  Similar department names found:")
                self.stdout.write(f"     {variations} (all map to '{normalized}')")
        
        if not issues_found:
            self.stdout.write("✅ No data quality issues found")
        
        # 3. Admin Dashboard Logic Simulation
        self.stdout.write(f"\n" + "=" * 80)
        self.stdout.write("3. ADMIN DASHBOARD LOGIC SIMULATION")
        self.stdout.write("=" * 80)
        
        # Replicate the exact logic from admin_dashboard view
        departments_raw = employees.values_list("department", flat=True).distinct()
        departments_set = set()
        
        # Normalize and deduplicate departments
        for dept in departments_raw:
            if dept and dept.strip():
                departments_set.add(dept.strip())
        
        # Get sorted unique departments
        departments_list = sorted(list(departments_set))
        
        self.stdout.write(f"\nAfter deduplication logic:")
        self.stdout.write(f"Unique departments: {len(departments_list)}")
        
        today = timezone.localtime().date()
        today_attendance = Attendance.objects.filter(date=today)
        
        total_shown = 0
        for dept in departments_list:
            # Filter employees by exact department match
            dept_emps = employees.filter(department=dept)
            dept_total = dept_emps.count()
            
            # Count present
            dept_present = today_attendance.filter(
                employee__department=dept,
                status__in=["PRESENT", "WFH", "ON_DUTY", "HALF_DAY"],
            ).count()
            
            percentage = round((dept_present / dept_total * 100) if dept_total > 0 else 0, 1)
            total_shown += dept_total
            
            self.stdout.write(f"  {dept}: {dept_present}/{dept_total} ({percentage}%)")
        
        self.stdout.write(f"\nTotal employees shown in dashboard: {total_shown}")
        self.stdout.write(f"Total active employees in DB: {employees.count()}")
        
        if total_shown != employees.count():
            self.stdout.write(self.style.ERROR(f"⚠️  MISMATCH! Dashboard shows {total_shown} but DB has {employees.count()}"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Counts match perfectly!"))
        
        # 4. Fix data issues if requested
        if fix_data and issues_found:
            self.stdout.write(f"\n" + "=" * 80)
            self.stdout.write("4. FIXING DATA ISSUES")
            self.stdout.write("=" * 80)
            
            fixed_count = 0
            
            # Fix whitespace issues
            for emp in employees:
                if emp.department and emp.department.strip() != emp.department:
                    old_dept = emp.department
                    emp.department = emp.department.strip()
                    emp.save()
                    fixed_count += 1
                    self.stdout.write(f"  Fixed: '{old_dept}' -> '{emp.department}' for {emp.user.get_full_name()}")
            
            if fixed_count > 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Fixed {fixed_count} department whitespace issues"))
            else:
                self.stdout.write("No whitespace issues to fix")
        
        # 5. Recommendations
        self.stdout.write(f"\n" + "=" * 80)
        self.stdout.write("5. RECOMMENDATIONS")
        self.stdout.write("=" * 80)
        
        if null_dept_count > 0:
            self.stdout.write("📝 Assign departments to employees with NULL/empty department")
        
        if whitespace_issues:
            self.stdout.write("📝 Run with --fix-data to clean whitespace issues")
        
        if similar_found:
            self.stdout.write("📝 Consider standardizing similar department names")
        
        self.stdout.write("📝 Ensure all employees have is_active=True if they should appear in dashboard")
        
        self.stdout.write(f"\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("DEBUG REPORT COMPLETE"))
        self.stdout.write("=" * 80)