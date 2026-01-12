# Leave Allocation System Guide

## Overview
The leave allocation system provides company-specific monthly leave accrual with different rates for different companies. The system automatically manages leave balances, provides monthly accrual functionality, and **preserves manual admin adjustments**.

## Key Features
- ✅ **Company-specific monthly accrual rates**
- ✅ **Preserves manual admin adjustments** (previous leaves, carry-forwards)
- ✅ **Flexible leave addition tools** for admins
- ✅ **Audit trail** for manual adjustments
- ✅ **Dry-run testing** for all operations

## Company-Specific Leave Rules

### Petabytz
- **Casual Leave (CL)**: 1.0 per month
- **Sick Leave (SL)**: 1.0 per month
- **Earned Leave (EL)**: 0.0 (no monthly accrual)

### SoftStandards
- **Casual Leave (CL)**: 0.5 per month
- **Sick Leave (SL)**: 0.5 per month
- **Earned Leave (EL)**: 0.0 (no monthly accrual)

### Bluebix
- **Casual Leave (CL)**: 0.5 per month
- **Sick Leave (SL)**: 0.5 per month
- **Earned Leave (EL)**: 0.0 (no monthly accrual)

## Current Status (February 2026)

### Leave Balances Allocated
```
Petabytz (11 employees):
├── Casual Leave: 2.0 per employee (1.0 × 2 months)
├── Sick Leave: 2.0 per employee (1.0 × 2 months)
└── Earned Leave: 0.0 per employee

SoftStandards (9 employees):
├── Casual Leave: 1.0 per employee (0.5 × 2 months)
├── Sick Leave: 1.0 per employee (0.5 × 2 months)
└── Earned Leave: 0.0 per employee

Bluebix (1 employee):
├── Casual Leave: 1.0 per employee (0.5 × 2 months)
├── Sick Leave: 1.0 per employee (0.5 × 2 months)
└── Earned Leave: 0.0 per employee
```

### Recent Updates
- **January 2026**: Initial setup completed with all leave balances reset to 0 and January allocation applied
- **February 2026**: Monthly accrual successfully executed on January 10, 2026
- **System Status**: ✅ Fully operational and ready for ongoing monthly accruals

## Management Commands

### 1. Initial Setup Command
```bash
# Reset all leave balances and set up from January 2026
python manage.py setup_monthly_leave_allocation --reset

# Setup for specific company only
python manage.py setup_monthly_leave_allocation --company-id 1 --reset
```

**What it does:**
- Resets all existing leave balances to 0
- Calculates total allocation from January 2026 to current month
- Applies company-specific monthly rates
- Creates LeaveBalance records for employees without them

### 2. Monthly Accrual Command
```bash
# Accrue leaves for current month (preserves manual adjustments)
python manage.py accrue_monthly_leaves_by_company

# Accrue leaves for specific month/year
python manage.py accrue_monthly_leaves_by_company --month 2 --year 2026

# Dry run to see what would be accrued
python manage.py accrue_monthly_leaves_by_company --month 2 --year 2026 --dry-run

# Accrue for specific company only
python manage.py accrue_monthly_leaves_by_company --company-id 1

# Override manual adjustments (not recommended)
python manage.py accrue_monthly_leaves_by_company --preserve-manual=False
```

**What it does:**
- Adds monthly leave allocation to existing balances
- **Preserves manual admin adjustments by default**
- Uses company-specific rates
- Can be run for any month/year
- Supports dry-run mode for testing

### 3. Add Previous/Carry-forward Leaves Command (NEW)
```bash
# Add previous leaves to specific employee
python manage.py add_previous_leaves --employee-id 1 --casual-leave 5.0 --sick-leave 3.0

# Add leaves to all employees in a company
python manage.py add_previous_leaves --company-id 1 --casual-leave 2.5 --earned-leave 1.0

# Test before applying
python manage.py add_previous_leaves --employee-id 1 --casual-leave 5.0 --dry-run

# Add with custom reason for audit trail
python manage.py add_previous_leaves --employee-id 1 --casual-leave 5.0 --reason "2025 carry-forward"
```

**What it does:**
- Adds previous/carry-forward leaves to employee balances
- Supports decimal values (e.g., 2.5 days)
- Works for individual employees or entire companies
- Tracks changes in audit trail (carry_forward_leave field)
- **These adjustments are preserved during monthly accrual**

## Monthly Accrual Schedule

### Recommended Schedule
Run the monthly accrual command on the 1st of each month:

```bash
# February 2026
python manage.py accrue_monthly_leaves_by_company --month 2 --year 2026

# March 2026
python manage.py accrue_monthly_leaves_by_company --month 3 --year 2026

# And so on...
```

### Projected Leave Balances

#### After 6 Months (June 2026):
```
Petabytz employees:
├── Casual Leave: 6.0 (1.0 × 6 months)
├── Sick Leave: 6.0 (1.0 × 6 months)

SoftStandards & Bluebix employees:
├── Casual Leave: 3.0 (0.5 × 6 months)
├── Sick Leave: 3.0 (0.5 × 6 months)
```

#### After 12 Months (December 2026):
```
Petabytz employees:
├── Casual Leave: 12.0 (1.0 × 12 months)
├── Sick Leave: 12.0 (1.0 × 12 months)

SoftStandards & Bluebix employees:
├── Casual Leave: 6.0 (0.5 × 12 months)
├── Sick Leave: 6.0 (0.5 × 12 months)
```

#### Current Progress (February 2026):
```
✅ Completed Months: January 2026, February 2026
📅 Next Accrual Due: March 1, 2026

Petabytz employees: 2.0 CL + 2.0 SL (16.7% of annual target)
SoftStandards & Bluebix employees: 1.0 CL + 1.0 SL (16.7% of annual target)
```

## Admin Manual Leave Management

### Adding Previous/Carry-forward Leaves

Admins can add previous year carry-forwards or additional leaves using multiple methods:

#### Method 1: Command Line (Recommended)
```bash
# Add 5 CL and 3 SL to specific employee
python manage.py add_previous_leaves --employee-id 1 --casual-leave 5.0 --sick-leave 3.0 --reason "2025 carry-forward"

# Add 2.5 CL to all employees in Petabytz company
python manage.py add_previous_leaves --company-id 1 --casual-leave 2.5 --reason "Bonus allocation"

# Test before applying
python manage.py add_previous_leaves --employee-id 1 --casual-leave 5.0 --dry-run
```

#### Method 2: Django Admin Interface
1. Navigate to **Employees → Leave Balances**
2. Find the employee's leave balance record
3. Edit the `casual_leave_allocated`, `sick_leave_allocated`, etc. fields
4. Add the additional leaves to existing values
5. Save the record

#### Method 3: Bulk Update via Admin
```python
# Example: Add 2 CL to all Petabytz employees
from employees.models import LeaveBalance, Employee
from companies.models import Company

company = Company.objects.get(name='Petabytz')
employees = Employee.objects.filter(company=company, is_active=True)

for emp in employees:
    balance = emp.leave_balance
    balance.casual_leave_allocated += 2.0
    balance.carry_forward_leave += 2.0  # For audit trail
    balance.save()
```

### Important Notes
- ✅ **Manual adjustments are preserved** during monthly accrual
- ✅ **Monthly accrual adds to existing balances**, doesn't overwrite
- ✅ **Audit trail** maintained in `carry_forward_leave` field
- ✅ **Decimal values supported** (e.g., 2.5 days)
- ✅ **Company-wide or individual** employee updates supported

## Leave Balance Management

### Database Structure
```python
class LeaveBalance(models.Model):
    employee = models.OneToOneField(Employee)
    
    # Allocations (what employee has earned)
    casual_leave_allocated = models.FloatField()
    sick_leave_allocated = models.FloatField()
    earned_leave_allocated = models.FloatField()
    
    # Usage (what employee has used)
    casual_leave_used = models.FloatField()
    sick_leave_used = models.FloatField()
    earned_leave_used = models.FloatField()
    
    # Calculated properties
    @property
    def casual_leave_balance(self):
        return self.casual_leave_allocated - self.casual_leave_used
```

### Leave Types
1. **Casual Leave (CL)**: For personal reasons, planned activities
2. **Sick Leave (SL)**: For medical reasons, illness
3. **Earned Leave (EL)**: Currently not accrued monthly (set to 0)
4. **Comp Off**: Compensatory off (not part of monthly accrual)

## Admin Interface

### Viewing Leave Balances
1. **Django Admin**: Navigate to Employees → Leave Balances
2. **Filter by Company**: Use company filter to see specific company balances
3. **Individual Employee**: View/edit individual employee leave balances

### Manual Adjustments
Admins can manually adjust leave balances through Django admin:
- Increase/decrease allocated leaves
- Record leave usage
- Add carry-forward leaves
- Mark lapsed leaves

## Integration with Leave Requests

### Leave Request Process
1. **Employee submits leave request** via system
2. **Manager/HR approves** the request
3. **System automatically deducts** from appropriate leave balance
4. **Balance updated** in real-time

### Leave Types Mapping
```python
LEAVE_TYPE_MAPPING = {
    'CL': 'casual_leave_used',      # Casual Leave
    'SL': 'sick_leave_used',        # Sick Leave
    'EL': 'earned_leave_used',      # Earned Leave
    'CO': 'comp_off_used',          # Comp Off
    'UL': 'unpaid_leave',           # Unpaid Leave (LOP)
}
```

## Automation & Scheduling

### Cron Job Setup
Set up monthly cron job to automatically accrue leaves:

```bash
# Add to crontab (runs on 1st of every month at 9 AM)
0 9 1 * * /path/to/python /path/to/manage.py accrue_monthly_leaves_by_company
```

### Notification System
Consider adding notifications for:
- Monthly leave accrual completion
- Low leave balance warnings
- Leave policy changes

## Reporting & Analytics

### Leave Balance Reports
The system provides:
- Individual employee leave balances
- Company-wise leave utilization
- Monthly accrual tracking
- Leave usage patterns

### Key Metrics
- **Accrual Rate**: Leaves earned per month by company
- **Utilization Rate**: Percentage of allocated leaves used
- **Balance Trends**: Leave balance changes over time
- **Company Comparison**: Leave usage across companies

## Troubleshooting

### Common Issues

#### 1. Employee Missing Leave Balance
**Problem**: New employee doesn't have leave balance
**Solution**: 
```bash
python manage.py setup_monthly_leave_allocation --company-id [company_id]
```

#### 2. Incorrect Monthly Accrual
**Problem**: Wrong amount accrued for a month
**Solution**: 
- Check company name matches exactly in leave_allocation_rules
- Verify employee's company assignment
- Use dry-run to test before applying

#### 3. Leave Balance Discrepancy
**Problem**: Balance doesn't match expected amount
**Solution**:
- Check leave usage records
- Verify manual adjustments in admin
- Review accrual history

### Verification Commands
```bash
# Check current leave balances
python -c "
from employees.models import LeaveBalance
for balance in LeaveBalance.objects.select_related('employee__company'):
    print(f'{balance.employee.user.get_full_name()} ({balance.employee.company.name}): CL={balance.casual_leave_balance}, SL={balance.sick_leave_balance}')
"

# Check company-wise summary
python -c "
from employees.models import Employee
from companies.models import Company
for company in Company.objects.all():
    employees = Employee.objects.filter(company=company, is_active=True)
    print(f'{company.name}: {employees.count()} active employees')
"
```

## Future Enhancements

### Planned Features
1. **Automatic Cron Integration**: Built-in scheduling
2. **Leave Policy Templates**: Predefined company policies
3. **Carry-forward Rules**: Automatic year-end processing
4. **Leave Lapse Management**: Automatic expiry handling
5. **Advanced Reporting**: Detailed analytics dashboard

### Customization Options
- **Variable Accrual Rates**: Different rates for different employee levels
- **Probation Period Rules**: Reduced accrual during probation
- **Location-based Policies**: Different rules for different locations
- **Seasonal Adjustments**: Modified accrual during specific periods

## Conclusion

The leave allocation system provides:
- **Company-specific Rules**: Different accrual rates per company
- **Automated Processing**: Monthly accrual with minimal manual intervention
- **Flexible Management**: Easy adjustments and corrections
- **Integration Ready**: Works with existing leave request system
- **Scalable Design**: Supports multiple companies and policies

The system is now configured and ready for ongoing monthly leave accrual based on the specified company rules.