"""
Test script to verify department employee counts
"""
from employees.models import Employee
from collections import Counter

# Get all active employees
employees = Employee.objects.filter(is_active=True)

print("=" * 70)
print("DEPARTMENT EMPLOYEE COUNT VERIFICATION")
print("=" * 70)

# Method 1: Using Counter (what we see in database)
dept_list = employees.values_list('department', flat=True)
dept_counts = Counter(dept_list)

print("\n1. Raw Department Counts (from database):")
print("-" * 70)
for dept, count in sorted(dept_counts.items()):
    if dept:
        print(f"  {dept}: {count} employees")

# Method 2: Using the deduplication logic (what admin dashboard uses)
departments_raw = employees.values_list("department", flat=True).distinct()
departments_set = set()

for dept in departments_raw:
    if dept and dept.strip():
        departments_set.add(dept.strip())

departments_list = sorted(list(departments_set))

print("\n2. After Deduplication (what dashboard shows):")
print("-" * 70)
for dept in departments_list:
    dept_emps = employees.filter(department=dept)
    dept_total = dept_emps.count()
    print(f"  {dept}: {dept_total} employees")

# Method 3: Check for whitespace issues
print("\n3. Checking for whitespace/case issues:")
print("-" * 70)
dept_variations = {}
for dept in dept_list:
    if dept:
        normalized = dept.strip()
        if normalized not in dept_variations:
            dept_variations[normalized] = []
        dept_variations[normalized].append(dept)

for normalized, variations in sorted(dept_variations.items()):
    if len(variations) > 1 or variations[0] != normalized:
        print(f"  '{normalized}' has variations: {variations}")

print("\n" + "=" * 70)
print(f"Total Active Employees: {employees.count()}")
print(f"Unique Departments (after dedup): {len(departments_list)}")
print("=" * 70)
