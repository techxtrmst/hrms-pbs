# Complete Attendance System Guide

## System Overview

The attendance report system automatically generates accurate attendance data for each company and location by integrating:
- **Company-specific holidays** configured by admins
- **Individual employee week-offs** 
- **Real-time attendance records**
- **Location-based configurations**

## How It Works

### 1. Multi-Company & Multi-Location Support

#### Company Structure
```
Company A (Petabytz)
├── India Location
│   ├── Employees: 11
│   └── Holidays: Republic Day, Independence Day, Diwali
├── USA Location  
│   ├── Employees: 0
│   └── Holidays: Independence Day, Thanksgiving, Christmas
└── Bangladesh Location
    ├── Employees: 0
    └── Holidays: Language Day, Independence Day, Victory Day

Company B (SoftStandards)
├── India Location
│   ├── Employees: 9
│   └── Holidays: Republic Day, Independence Day, Diwali
└── [Similar structure for other locations]
```

### 2. Automatic Status Detection Logic

When generating attendance reports, the system checks each date for each employee:

```python
# Priority order for status determination:
if attendance_record_exists:
    status = attendance_record.status
    if status == "WFH":
        display = "P"  # Count WFH as Present
    else:
        display = status_mapping[status]
else:
    # No attendance record exists
    if is_holiday_for_employee_location(date):
        status = "HOLIDAY"
        display = "H"
    elif is_weekoff_for_employee(date):
        status = "WEEKLY_OFF" 
        display = "WO"
    else:
        status = "ABSENT"
        display = "A"
```

### 3. Holiday Detection Process

#### Step 1: Location-Based Holiday Lookup
```python
# Get holidays for employee's specific company + location
holidays = Holiday.objects.filter(
    company=employee.company,
    location=employee.location,
    date=target_date,
    is_active=True
)
```

#### Step 2: Automatic Application
- If holiday exists → Mark as "H" in report
- Include in holiday count statistics
- Exclude from working days calculation

### 4. Week-off Detection Process

#### Step 1: Individual Employee Configuration
```python
# Check employee's personal week-off settings
weekoff_map = {
    0: employee.week_off_monday,    # Monday
    1: employee.week_off_tuesday,   # Tuesday
    2: employee.week_off_wednesday, # Wednesday
    3: employee.week_off_thursday,  # Thursday
    4: employee.week_off_friday,    # Friday
    5: employee.week_off_saturday,  # Saturday
    6: employee.week_off_sunday,    # Sunday
}
is_weekoff = weekoff_map[date.weekday()]
```

#### Step 2: Automatic Application
- If week-off → Mark as "WO" in report
- Include in week-off count statistics
- Exclude from working days calculation

## Admin Configuration Workflow

### 1. Holiday Setup Process

#### Method 1: Admin Panel (Manual)
1. **Access**: Django Admin → Companies → Holidays
2. **Create**: Add Holiday with Company + Location + Date
3. **Apply**: Run `python manage.py mark_holidays --days 365`

#### Method 2: Bulk Setup (Automated)
1. **Setup**: Run `python manage.py setup_sample_holidays --year 2026`
2. **Apply**: Run `python manage.py mark_holidays --days 365`

### 2. Week-off Setup Process

#### Method 1: Individual Employee (Manual)
1. **Access**: Django Admin → Employees → Employee
2. **Configure**: Set week-off checkboxes for each day
3. **Apply**: Run `python manage.py mark_week_offs --days 365`

#### Method 2: Bulk Update (Programmatic)
```python
# Example: Set all employees to Sat+Sun weekoff
Employee.objects.all().update(
    week_off_saturday=True,
    week_off_sunday=True,
    week_off_monday=False,
    # ... other days
)
```

## Report Generation Features

### 1. Current Date Limitation
- **Logic**: Only shows data up to current date
- **Benefit**: No confusing future empty dates
- **Implementation**: `if end_date > today: end_date = today`

### 2. WFH as Present
- **Logic**: WFH counted as Present attendance
- **Display**: Shows "P" instead of separate "WFH"
- **Calculation**: Included in attendance percentage

### 3. Working Days Calculation
```python
working_days = total_days - weekly_offs - holidays
attendance_percentage = (present_days / working_days) * 100
```

### 4. Location Filtering
- **Feature**: Filter report by specific location
- **Benefit**: See location-specific holidays and employees
- **Usage**: Dropdown in report interface

## Status Codes Reference

| Code | Meaning | Counted As | Notes |
|------|---------|------------|-------|
| P | Present | Present | Includes WFH |
| A | Absent | Absent | Working day absence |
| L | Leave | Leave | Approved leave |
| HD | Half Day | Half Day | Partial attendance |
| WO | Weekly Off | Non-working | Employee-specific |
| H | Holiday | Non-working | Location-specific |

## Data Flow Example

### Scenario: Employee "John" on Republic Day (Jan 26, 2026)

1. **Employee Details**:
   - Company: Petabytz
   - Location: India
   - Week-offs: Saturday, Sunday

2. **Date Check**: January 26, 2026 (Sunday)

3. **System Logic**:
   ```python
   # Check attendance record
   attendance = get_attendance(john, jan_26_2026)
   # Result: None (no record)
   
   # Check holiday
   holiday = get_holiday(petabytz, india, jan_26_2026)
   # Result: "Republic Day" found
   
   # Final status: "HOLIDAY" → Display: "H"
   ```

4. **Report Display**: Shows "H" for Jan 26
5. **Statistics**: Counted in holiday total, excluded from working days

## Management Commands Summary

### Holiday Management
```bash
# Setup sample holidays for all companies
python manage.py setup_sample_holidays --year 2026

# Setup for specific company
python manage.py setup_sample_holidays --company-id 1

# Apply holidays to attendance records
python manage.py mark_holidays --days 365

# Apply for specific company
python manage.py mark_holidays --company-id 1 --days 365
```

### Week-off Management
```bash
# Apply week-offs for all employees
python manage.py mark_week_offs --days 365

# Apply for specific employee
python manage.py mark_week_offs --employee-id 123

# Apply for date range
python manage.py mark_week_offs --days 30
```

## Integration Benefits

### 1. Automatic Accuracy
- No manual holiday marking needed
- Consistent application across all employees
- Location-aware holiday detection

### 2. Scalability
- Supports unlimited companies and locations
- Individual employee configurations
- Bulk management capabilities

### 3. Compliance
- Meets local holiday requirements
- Flexible week-off patterns
- Accurate payroll calculations

### 4. User Experience
- Clean, simplified interface
- Automatic status detection
- Real-time report generation

## Verification Steps

### 1. Test Holiday Detection
```python
# Check if holiday exists for employee
holiday = Holiday.objects.filter(
    company=employee.company,
    location=employee.location,
    date=test_date,
    is_active=True
).exists()
```

### 2. Test Week-off Detection
```python
# Check employee week-off configuration
is_weekoff = employee.is_week_off(test_date)
```

### 3. Test Report Generation
- Access: `/analytics/report/`
- Filter: Select month, year, location
- Verify: Holiday dates show "H", week-offs show "WO"

## Current System Status

✅ **Implemented Features:**
- Multi-company holiday management
- Location-specific holiday detection
- Individual employee week-off configuration
- Automatic status detection in reports
- WFH counted as present attendance
- Current date limitation
- Excel export with same logic

✅ **Sample Data:**
- 64 holidays configured across 4 companies
- 10 locations with specific holiday calendars
- 22 active employees with week-off configurations

✅ **Verified Functionality:**
- Holiday detection working for all companies
- Week-off detection working for all employees
- Attendance report generating correctly
- Excel export matching web report

The system is fully operational and ready for production use with proper holiday and week-off management for multiple companies and locations.