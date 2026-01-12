# Admin Guide: Holiday and Week-off Management

## Overview
This guide explains how administrators can configure holidays and week-offs for different companies and locations, and how these settings automatically affect the attendance reports.

## Holiday Management

### 1. Adding Holidays via Admin Panel

#### Step 1: Access Holiday Management
1. Login to Django Admin: `/admin/`
2. Navigate to **Companies > Holidays**
3. Click **Add Holiday**

#### Step 2: Configure Holiday Details
```
Company: [Select Company]
Location: [Select Location within Company]
Name: [Holiday Name, e.g., "Republic Day"]
Date: [Holiday Date]
Holiday Type: 
  - MANDATORY: Required holiday for all employees
  - OPTIONAL: Employees can choose to take
  - RESTRICTED: Limited availability
Description: [Optional details]
Year: [Auto-populated from date]
Is Active: ✓ [Check to enable]
```

#### Step 3: Save and Apply
1. Click **Save**
2. Run management command to apply to attendance:
   ```bash
   python manage.py mark_holidays --days 365
   ```

### 2. Bulk Holiday Setup

#### Using Management Command
```bash
# Setup sample holidays for all companies
python manage.py setup_sample_holidays --year 2026

# Setup for specific company
python manage.py setup_sample_holidays --company-id 1 --year 2026
```

#### Sample Holidays Included
**India Locations:**
- Republic Day (Jan 26)
- Holi (Mar 14)
- Independence Day (Aug 15)
- Gandhi Jayanti (Oct 2)
- Diwali (Oct 31)
- Christmas (Dec 25)

**USA Locations:**
- New Year Day (Jan 1)
- Martin Luther King Jr. Day (Jan 20)
- Presidents Day (Feb 17)
- Memorial Day (May 26)
- Independence Day (Jul 4)
- Labor Day (Sep 1)
- Thanksgiving (Nov 27)
- Christmas (Dec 25)

**Bangladesh Locations:**
- International Mother Language Day (Feb 21)
- Independence Day (Mar 26)
- Bengali New Year (Apr 14)
- Victory Day (Dec 16)

### 3. Holiday Configuration by Location

#### Location-Specific Holidays
- Each holiday is tied to a specific **Company + Location** combination
- Employees only see holidays for their assigned location
- Same company can have different holidays for different locations

#### Example Configuration:
```
Company: Petabytz
├── India Location
│   ├── Republic Day (Jan 26)
│   ├── Independence Day (Aug 15)
│   └── Diwali (Oct 31)
├── USA Location
│   ├── Independence Day (Jul 4)
│   ├── Thanksgiving (Nov 27)
│   └── Christmas (Dec 25)
└── Bangladesh Location
    ├── Independence Day (Mar 26)
    └── Victory Day (Dec 16)
```

## Week-off Management

### 1. Individual Employee Week-offs

#### Step 1: Access Employee Management
1. Navigate to **Employees > Employees**
2. Select employee to edit
3. Scroll to **Week-off Configuration** section

#### Step 2: Configure Week-offs
```
Week-off Monday: ☐
Week-off Tuesday: ☐
Week-off Wednesday: ☐
Week-off Thursday: ☐
Week-off Friday: ☐
Week-off Saturday: ☑ [Default]
Week-off Sunday: ☑ [Default]
```

#### Step 3: Apply Changes
1. Save employee record
2. Run management command:
   ```bash
   python manage.py mark_week_offs --days 365
   ```

### 2. Bulk Week-off Configuration

#### Common Patterns:
- **Standard**: Saturday + Sunday
- **Middle East**: Friday + Saturday
- **Retail**: Tuesday + Wednesday
- **Custom**: Any combination

#### Management Command:
```bash
# Apply week-offs for all employees
python manage.py mark_week_offs --days 60

# Apply for specific employee
python manage.py mark_week_offs --employee-id 123 --days 60
```

## Attendance Report Integration

### 1. Automatic Holiday Detection

The attendance report automatically:
- Detects holidays based on employee's company and location
- Shows "H" for holiday dates
- Excludes holidays from working days calculation
- Applies to attendance percentage calculation

### 2. Automatic Week-off Detection

The system automatically:
- Uses individual employee week-off configuration
- Shows "WO" for week-off dates
- Excludes week-offs from working days calculation
- Supports different week-off patterns per employee

### 3. Attendance Calculation Logic

```
Working Days = Total Days - Weekly Offs - Holidays
Present Days = Present + WFH (counted together)
Attendance % = Present Days / Working Days × 100
```

### 4. Status Priority (when no attendance record exists):
1. **Holiday** (if date matches company+location holiday)
2. **Weekly Off** (if date matches employee week-off)
3. **Absent** (default for working days)

## Management Commands Reference

### Holiday Commands
```bash
# Setup sample holidays
python manage.py setup_sample_holidays --year 2026

# Mark holidays in attendance records
python manage.py mark_holidays --days 365

# Mark holidays for specific company
python manage.py mark_holidays --company-id 1 --days 365
```

### Week-off Commands
```bash
# Mark week-offs for all employees
python manage.py mark_week_offs --days 365

# Mark week-offs for specific employee
python manage.py mark_week_offs --employee-id 123 --days 30
```

## Best Practices

### 1. Holiday Setup
- Set up holidays at the beginning of each year
- Use location-specific holidays for multinational companies
- Mark holidays as MANDATORY for company-wide observance
- Use OPTIONAL for flexible holidays

### 2. Week-off Configuration
- Configure week-offs during employee onboarding
- Consider local customs and business requirements
- Update week-offs when employees change locations
- Run mark_week_offs command after bulk changes

### 3. Attendance Report Usage
- Filter by location to see location-specific holidays
- Export to Excel for payroll processing
- Review attendance percentages for performance evaluation
- Use working days calculation for accurate metrics

## Troubleshooting

### Issue: Holidays not showing in report
**Solution:**
1. Verify holiday exists for correct company+location
2. Check holiday is marked as active
3. Run `mark_holidays` command
4. Refresh attendance report

### Issue: Week-offs not applied
**Solution:**
1. Check employee week-off configuration
2. Run `mark_week_offs` command
3. Verify employee has location assigned
4. Check date range in report

### Issue: Incorrect attendance percentage
**Solution:**
1. Verify working days calculation
2. Check if holidays/week-offs are properly excluded
3. Ensure WFH is counted as present
4. Review date range (only shows up to current date)

## API Integration

### Holiday API Endpoints
```python
# Get holidays for company/location
GET /api/holidays/?company=1&location=2&year=2026

# Create holiday
POST /api/holidays/
{
    "company": 1,
    "location": 2,
    "name": "New Holiday",
    "date": "2026-12-31",
    "holiday_type": "MANDATORY"
}
```

### Employee Week-off API
```python
# Update employee week-offs
PATCH /api/employees/123/
{
    "week_off_saturday": true,
    "week_off_sunday": true,
    "week_off_friday": false
}
```

## Conclusion

The holiday and week-off management system provides:
- **Flexibility**: Different configurations per company/location
- **Automation**: Automatic detection in attendance reports
- **Accuracy**: Proper working days and attendance calculations
- **Scalability**: Supports multiple companies and locations
- **Compliance**: Meets local holiday and working day requirements

For additional support, contact the system administrator or refer to the Django admin documentation.