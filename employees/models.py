from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from loguru import logger

from companies.models import Company


class Employee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="employees")
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinates_user",
    )
    profile_picture = models.ImageField(upload_to="employee_avatars/", null=True, blank=True)

    # Personal Details
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    personal_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Personal Email",
        help_text="Personal Email Address for information only",
    )
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    MARITAL_STATUS_CHOICES = [
        ("S", "Single"),
        ("M", "Married"),
        ("D", "Divorced"),
        ("W", "Widowed"),
    ]
    marital_status = models.CharField(max_length=1, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)
    dob = models.DateField(verbose_name="Date of Birth", null=True, blank=True)
    permanent_address = models.TextField(blank=True, null=True)
    current_address = models.TextField(blank=True, null=True, verbose_name="Current Address")
    profile_edited = models.BooleanField(default=False, help_text="Has the employee edited their profile?")
    emergency_contact = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Legacy field - use EmergencyContact model instead",
    )
    badge_id = models.CharField(max_length=20, unique=True, null=True, verbose_name="Employee ID")

    # Job Profile
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    WORK_TYPE_CHOICES = [
        ("FT", "Full Time"),
        ("PT", "Part Time"),
        ("CT", "Contract"),
        ("RM", "Remote"),
    ]
    work_type = models.CharField(max_length=2, choices=WORK_TYPE_CHOICES, default="FT")
    assigned_shift = models.ForeignKey(
        "companies.ShiftSchedule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_employees",
    )
    shift_schedule = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Legacy: Assigned shift schedule (e.g., 09:00 AM - 06:00 PM)",
    )
    date_of_joining = models.DateField(null=True, blank=True)

    # Location (for holiday filtering)
    location = models.ForeignKey(
        "companies.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        help_text="Employee work location for holiday filtering",
    )

    # Financial Details
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="IFSC Code")
    uan = models.CharField(max_length=20, blank=True, null=True, verbose_name="UAN")
    pan_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="PAN Number")
    pf_enabled = models.BooleanField(default=False, verbose_name="Provident Fund")
    annual_ctc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Annual CTC",
    )

    # Exit Management Fields
    EMPLOYMENT_STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("RESIGNED", "Resigned"),
        ("ABSCONDED", "Absconded"),
        ("TERMINATED", "Terminated"),
    ]
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        default="ACTIVE",
        help_text="Current employment status",
    )
    exit_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Last Working Date",
        help_text="Date when employee exited the organization",
    )
    exit_note = models.TextField(
        null=True,
        blank=True,
        verbose_name="Exit Reason/Note",
        help_text="Detailed reason for employee exit",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether employee is currently active in the organization",
    )

    # Week-off Configuration (Individual employee week-offs)
    week_off_monday = models.BooleanField(default=False, help_text="Monday is week-off")
    week_off_tuesday = models.BooleanField(default=False, help_text="Tuesday is week-off")
    week_off_wednesday = models.BooleanField(default=False, help_text="Wednesday is week-off")
    week_off_thursday = models.BooleanField(default=False, help_text="Thursday is week-off")
    week_off_friday = models.BooleanField(default=False, help_text="Friday is week-off")
    week_off_saturday = models.BooleanField(default=True, help_text="Saturday is week-off")
    week_off_sunday = models.BooleanField(default=True, help_text="Sunday is week-off")

    # Email Notification Tracking
    last_birthday_email_year = models.IntegerField(null=True, blank=True, help_text="Year of last sent birthday email")
    last_anniversary_email_year = models.IntegerField(
        null=True, blank=True, help_text="Year of last sent anniversary email"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.designation})"

    def is_week_off(self, date):
        """Check if the given date is a week-off for this employee"""
        day_of_week = date.weekday()  # 0=Monday, 6=Sunday
        week_off_map = {
            0: self.week_off_monday,
            1: self.week_off_tuesday,
            2: self.week_off_wednesday,
            3: self.week_off_thursday,
            4: self.week_off_friday,
            5: self.week_off_saturday,
            6: self.week_off_sunday,
        }
        return week_off_map.get(day_of_week, False)

    def get_probation_status(self):
        """
        Get probation status for the employee
        Returns:
        - 'IN_PROBATION': Employee is still in probation period (< 3 months)
        - 'COMPLETED': Employee has completed probation period (>= 3 months)
        - 'COMPLETED_TODAY': Employee completed probation today (exactly 3 months)
        """
        if not self.date_of_joining:
            return 'IN_PROBATION'
        
        from dateutil.relativedelta import relativedelta
        from django.utils import timezone
        
        today = timezone.now().date()
        probation_end_date = self.date_of_joining + relativedelta(months=3)
        
        if today < probation_end_date:
            return 'IN_PROBATION'
        elif today == probation_end_date:
            return 'COMPLETED_TODAY'
        else:
            return 'COMPLETED'
    
    def get_probation_end_date(self):
        """Get the exact date when probation period ends (3 months from joining)"""
        if not self.date_of_joining:
            return None
        
        from dateutil.relativedelta import relativedelta
        return self.date_of_joining + relativedelta(months=3)
    
    def is_probation_completed(self):
        """Check if employee has completed probation period"""
        status = self.get_probation_status()
        return status in ['COMPLETED', 'COMPLETED_TODAY']

    def save(self, *args, **kwargs):
        """Auto-generate employee ID if not set"""
        if not self.badge_id and self.location:
            # Generate employee ID based on location
            location_name = self.location.name.upper()

            # Determine prefix based on location
            if "HYDERABAD" in location_name or "HYD" in location_name:
                if self.company.name.upper() in ["PETABYTZ", "PETABYTES"]:
                    prefix = "PBTHYD"
                elif self.company.name.upper() in ["SOFTSTANDARD", "SOFT STANDARD"]:
                    prefix = "SSSHYD"
                else:
                    # Default prefix for other companies in Hyderabad
                    prefix = "EMPHYD"
            else:
                # For other locations, use first 3 letters of company + first 3 of location
                company_code = self.company.name[:3].upper()
                location_code = location_name[:3].upper()
                prefix = f"{company_code}{location_code}"

            # Get the last employee with this prefix
            last_employee = Employee.objects.filter(badge_id__startswith=prefix).order_by("-badge_id").first()

            if last_employee and last_employee.badge_id:
                # Extract the number part and increment
                try:
                    last_number = int(last_employee.badge_id[len(prefix) :])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1

            # Format: PREFIX + 3-digit number (e.g., PBTHYD001)
            self.badge_id = f"{prefix}{new_number:03d}"

        super().save(*args, **kwargs)


class EmergencyContact(models.Model):
    """
    Model to store multiple emergency contacts for each employee
    """

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="emergency_contacts")
    name = models.CharField(max_length=100, help_text="Full name of emergency contact")
    phone_number = models.CharField(max_length=15, help_text="Contact phone number")
    relationship = models.CharField(
        max_length=50,
        help_text="Relationship to employee (e.g., Spouse, Parent, Sibling)",
    )
    is_primary = models.BooleanField(default=False, help_text="Primary emergency contact")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "created_at"]
        verbose_name = "Emergency Contact"
        verbose_name_plural = "Emergency Contacts"

    def __str__(self):
        return f"{self.name} ({self.relationship}) - {self.employee.user.get_full_name()}"

    def save(self, *args, **kwargs):
        """Ensure only one primary contact per employee"""
        if self.is_primary:
            # Set all other contacts for this employee to non-primary
            EmergencyContact.objects.filter(employee=self.employee, is_primary=True).exclude(pk=self.pk).update(
                is_primary=False
            )
        super().save(*args, **kwargs)


class EmployeeIDProof(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="id_proofs")
    aadhar_front = models.ImageField(upload_to="id_proofs/aadhar/", null=True, blank=True)
    aadhar_back = models.ImageField(upload_to="id_proofs/aadhar/", null=True, blank=True)
    pan_card = models.ImageField(upload_to="id_proofs/pan/", null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ID Proofs - {self.employee.user.get_full_name()}"


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField()
    clock_in = models.DateTimeField(null=True, blank=True)  # First clock-in of the day
    clock_out = models.DateTimeField(null=True, blank=True)  # Last clock-out of the day
    STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("HALF_DAY", "Half Day"),
        ("LEAVE", "On Leave"),
        ("WFH", "Work From Home"),
        ("ON_DUTY", "On Duty"),
        ("WEEKLY_OFF", "Weekly Off"),
        ("HOLIDAY", "Holiday"),
        ("MISSING_PUNCH", "Missing Punch"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ABSENT")
    location_in = models.CharField(max_length=255, null=True, blank=True)  # Lat,Long
    location_out = models.CharField(max_length=255, null=True, blank=True)

    # Early/Late tracking
    is_late = models.BooleanField(default=False, help_text="Marked late based on shift timing")
    late_by_minutes = models.IntegerField(default=0, help_text="Minutes late after grace period")

    total_working_hours = models.FloatField(default=0.0, help_text="Total hours worked today across all sessions")

    # Grace Period Logic
    is_grace_used = models.BooleanField(default=False, help_text="Logged in late but within grace period")
    is_half_day_late = models.BooleanField(default=False, help_text="Marked as Half Day due to late login exceed")

    is_early_departure = models.BooleanField(default=False, help_text="Left before shift end time")
    early_departure_minutes = models.IntegerField(default=0, help_text="Minutes before shift end")

    # Multiple click handling
    clock_in_attempts = models.IntegerField(default=0, help_text="Number of clock-in attempts (max 3)")
    daily_clock_count = models.IntegerField(default=0, help_text="Number of valid clock-ins today")
    is_currently_clocked_in = models.BooleanField(default=False, help_text="Currently clocked in status")
    max_daily_clocks = models.IntegerField(default=3, help_text="Maximum allowed clock-ins per day")

    # Working hours tracking
    total_working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Total working hours for the day",
    )

    # Location tracking
    location_tracking_active = models.BooleanField(
        default=False, help_text="Whether location tracking is currently active"
    )
    location_tracking_end_time = models.DateTimeField(
        null=True, blank=True, help_text="When location tracking should stop"
    )

    # Session tracking
    daily_sessions_count = models.IntegerField(default=0, help_text="Number of sessions today")
    max_daily_sessions = models.IntegerField(default=3, help_text="Maximum allowed sessions per day")
    current_session_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Current session type (WEB/REMOTE)",
    )

    # Timezone tracking
    user_timezone = models.CharField(
        max_length=50,
        default="Asia/Kolkata",
        help_text="User's timezone when attendance was recorded",
    )

    # Session tracking
    current_session_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ("WEB", "Web"),
            ("REMOTE", "Remote"),
        ],
        help_text="Current session type (WEB/REMOTE)",
    )

    class Meta:
        unique_together = [["employee", "date"]]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee} - {self.date}"

    def calculate_late_arrival(self):
        """Calculate if employee is late based on their shift schedule and location timezone"""
        from datetime import datetime, timedelta

        import pytz

        from companies.models import ShiftSchedule

        if not self.clock_in:
            return

        # Get location timezone
        tz_name = self.employee.location.timezone if self.employee.location else "Asia/Kolkata"
        local_tz = pytz.timezone(tz_name)

        # Convert clock_in to local timezone
        local_clock_in = self.clock_in.astimezone(local_tz)
        clock_in_time = local_clock_in.time()

        # Determine Shift
        shift = self.employee.assigned_shift
        if not shift:
            # Fallback (Legacy)
            if self.employee.shift_schedule:
                shift = ShiftSchedule.objects.filter(
                    company=self.employee.company,
                    name__iexact=self.employee.shift_schedule,
                ).first()
            if not shift:
                shift = ShiftSchedule.objects.filter(company=self.employee.company).first()

        if not shift:
            return

        # Calculate expected start time with grace period
        shift_start = shift.start_time
        grace_minutes = shift.grace_period_minutes

        # Convert to datetime for calculation
        shift_start_dt = datetime.combine(self.date, shift_start)
        grace_end_dt = shift_start_dt + timedelta(minutes=grace_minutes)
        clock_in_dt = datetime.combine(self.date, clock_in_time)

        # Reset flags first
        self.is_late = False
        self.is_grace_used = False
        self.is_half_day_late = False
        self.late_by_minutes = 0

        # Check Late Logic
        if clock_in_dt > shift_start_dt:
            if clock_in_dt <= grace_end_dt:
                # 1. Within Grace Period
                # Check how many times grace was used this month
                grace_count = (
                    Attendance.objects.filter(
                        employee=self.employee,
                        date__month=self.date.month,
                        date__year=self.date.year,
                        is_grace_used=True,
                    )
                    .exclude(pk=self.pk)
                    .count()
                )

                if grace_count >= shift.allowed_late_logins:
                    # Limit Exceeded -> Apply Penalty
                    if shift.grace_exceeded_action == "HALF_DAY":
                        self.is_half_day_late = True
                        if self.status not in ["ON_DUTY", "WFH", "LEAVE"]:
                            self.status = "HALF_DAY"
                        # We still mark grace used as they essentially used the time
                        self.is_grace_used = True
                    elif shift.grace_exceeded_action == "LOP":
                        self.is_half_day_late = True  # Using same flag but status might be different?
                        if self.status not in ["ON_DUTY", "WFH", "LEAVE"]:
                            self.status = "ABSENT"  # Or specific LOP status
                        self.is_grace_used = True
                    else:
                        # NONE or tracking only
                        self.is_grace_used = True
                else:
                    # Allowed
                    self.is_grace_used = True
                    # Status remains PRESENT (or whatever it was initialized as)

            else:
                # 2. Strictly Late (Beyond Grace)
                self.is_late = True
                self.late_by_minutes = int((clock_in_dt - grace_end_dt).total_seconds() / 60)
                # Usually Late Logic doesn't check grace count, you are just late.
                # But typically Late also implies "missed grace".

    def calculate_early_departure(self):
        """Calculate if employee left early based on location timezone"""
        from datetime import datetime

        import pytz

        if not self.clock_out:
            return

        # Get location timezone
        tz_name = self.employee.location.timezone if self.employee.location else "Asia/Kolkata"
        local_tz = pytz.timezone(tz_name)

        # Convert clock_out to local timezone
        local_clock_out = self.clock_out.astimezone(local_tz)
        clock_out_time = local_clock_out.time()

        # Get shift schedule
        from companies.models import ShiftSchedule

        shift = None
        if self.employee.shift_schedule:
            shift = ShiftSchedule.objects.filter(
                company=self.employee.company, name__iexact=self.employee.shift_schedule
            ).first()

        if not shift:
            shift = ShiftSchedule.objects.filter(company=self.employee.company).first()

        if not shift:
            return

        # Calculate expected end time
        shift_end = shift.end_time
        threshold_minutes = shift.early_departure_threshold_minutes

        # Convert to datetime for calculation
        shift_end_dt = datetime.combine(self.date, shift_end)
        threshold_dt = shift_end_dt - timedelta(minutes=threshold_minutes)
        clock_out_dt = datetime.combine(self.date, clock_out_time)

        if clock_out_dt < threshold_dt:
            self.is_early_departure = True
            self.early_departure_minutes = int((threshold_dt - clock_out_dt).total_seconds() / 60)
        else:
            self.is_early_departure = False
            self.early_departure_minutes = 0

    @property
    def effective_hours(self):
        """Calculate effective hours using session-based approach for accuracy"""
        try:
            # Use cumulative calculation including current session if active
            total_hours = self.get_cumulative_working_hours_including_current()
            
            if total_hours > 0:
                hours = int(total_hours)
                minutes = int((total_hours - hours) * 60)
                
                # Cap display at 24 hours
                if hours > 24:
                    hours = 24
                    minutes = 0
                
                # Show '+' if currently clocked in (active session)
                is_active = self.is_currently_clocked_in
                return f"{hours}:{minutes:02d}{'+' if is_active else ''}"
            
            return "0:00"
        except Exception as e:
            logger.error(f"Error calculating effective hours: {str(e)}")
            return "0:00"

    @property
    def visual_width(self):
        # Percentage for the visual bar (assuming 9 hours shift)
        if self.clock_in and self.clock_out:
            diff = self.clock_out - self.clock_in
            hours = diff.total_seconds() / 3600
            percent = max(0, min((hours / 9) * 100, 100))
            return percent
        elif self.clock_in:
            # If currently clocked in, calculate from clock_in to now (handled in view typically, but distinct here)
            pass
        return 0

    @property
    def attendance_status_display(self):
        """Display attendance status with late/early indicators"""
        status_text = self.get_status_display()
        if self.is_late:
            status_text += f" (Late by {self.late_by_minutes} min)"
        if self.is_early_departure:
            status_text += f" (Early by {self.early_departure_minutes} min)"
        return status_text

    def get_shift_completion_percentage(self):
        """Calculate what percentage of the shift has been completed"""
        # Get total worked hours from all completed sessions
        sessions = AttendanceSession.objects.filter(
            employee=self.employee,
            date=self.date,
            clock_in__isnull=False,
            clock_out__isnull=False,
        )

        total_minutes = 0
        for session in sessions:
            duration = session.clock_out - session.clock_in
            total_minutes += duration.total_seconds() / 60

        worked_hours = total_minutes / 60
        expected_hours = self.get_shift_duration_hours()

        if expected_hours > 0:
            percentage = (worked_hours / expected_hours) * 100
            return min(percentage, 100)  # Cap at 100%

        return 0

    def get_combined_session_summary(self):
        """Get a summary of all sessions combined for the day"""
        sessions = AttendanceSession.objects.filter(employee=self.employee, date=self.date).order_by("session_number")

    def calculate_total_working_hours(self):
        """Calculate total working hours from all completed sessions with 24-hour daily cap"""
        from datetime import datetime, time
        from decimal import Decimal

        sessions = AttendanceSession.objects.filter(
            employee=self.employee,
            date=self.date,
            clock_in__isnull=False,
        )

        total_seconds = 0
        attendance_date_end = datetime.combine(self.date, time(23, 59, 59))

        # Convert to timezone-aware datetime if needed
        if sessions.exists() and timezone.is_aware(sessions.first().clock_in):
            attendance_date_end = timezone.make_aware(attendance_date_end)

        for session in sessions:
            if session.clock_in:
                # Determine end time for this session
                if session.clock_out:
                    session_end = session.clock_out
                else:
                    # For active sessions, use current time but cap at end of day
                    session_end = min(timezone.now(), attendance_date_end)

                # Ensure session doesn't extend beyond the attendance date
                if session_end > attendance_date_end:
                    session_end = attendance_date_end

                # Calculate session duration
                if session_end > session.clock_in:
                    duration = session_end - session.clock_in
                    session_seconds = duration.total_seconds()

                    # Ensure non-negative duration
                    if session_seconds > 0:
                        total_seconds += session_seconds

        # Cap total hours at 24 hours (86400 seconds) per day
        if total_seconds > 86400:
            total_seconds = 86400

        # Convert to hours and round to 2 decimal places
        total_hours = Decimal(total_seconds / 3600).quantize(Decimal("0.01"))

        # Ensure maximum of 24.00 hours
        if total_hours > 24:
            total_hours = Decimal("24.00")

        self.total_working_hours = total_hours
        return total_hours

    def can_clock_in(self):
        """Check if employee can clock in"""
        # Can't clock in if already clocked in
        if self.is_currently_clocked_in:
            return False

        # Can't clock in if max sessions reached
        if self.daily_sessions_count >= self.max_daily_sessions:
            return False

        return True

    def can_clock_out(self):
        """Check if employee can clock out"""
        # Can only clock out if currently clocked in
        return self.is_currently_clocked_in

        completed_sessions = sessions.filter(clock_in__isnull=False, clock_out__isnull=False)

        active_sessions = sessions.filter(clock_in__isnull=False, clock_out__isnull=True)

        total_minutes = 0
        for session in completed_sessions:
            duration = session.clock_out - session.clock_in
            total_minutes += duration.total_seconds() / 60

        worked_hours = total_minutes / 60
        expected_hours = self.get_shift_duration_hours()

        return {
            "total_sessions": sessions.count(),
            "completed_sessions": completed_sessions.count(),
            "active_sessions": active_sessions.count(),
            "total_worked_hours": round(worked_hours, 2),
            "expected_hours": expected_hours,
            "completion_percentage": round((worked_hours / expected_hours) * 100, 1) if expected_hours > 0 else 0,
            "remaining_hours": max(0, expected_hours - worked_hours),
            "is_shift_complete": worked_hours >= expected_hours * 0.9,  # 90% completion threshold
        }

    def calculate_total_working_hours(self):
        """Calculate and update total working hours from all sessions"""
        try:
            from .models import AttendanceSession

            # Fetch all completed sessions for this attendance record
            sessions = AttendanceSession.objects.filter(
                employee=self.employee,
                date=self.date,
                clock_in__isnull=False,
                clock_out__isnull=False,
            )

            total_seconds = 0
            for session in sessions:
                duration = session.clock_out - session.clock_in
                total_seconds += duration.total_seconds()

            # Convert to hours
            self.total_working_hours = round(total_seconds / 3600, 2)
            self.save(update_fields=["total_working_hours"])
            return self.total_working_hours

        except Exception as e:
            logger.error(f"Error calculating total working hours: {str(e)}")
            return 0.0

    def get_cumulative_working_hours_including_current(self):
        """Calculate total working hours including current active session"""
        try:
            from django.utils import timezone
            from .models import AttendanceSession

            # Get all completed sessions for today
            completed_sessions = AttendanceSession.objects.filter(
                employee=self.employee,
                date=self.date,
                clock_in__isnull=False,
                clock_out__isnull=False,
            )
            
            # Calculate total hours from completed sessions
            total_seconds = 0
            for session in completed_sessions:
                duration = session.clock_out - session.clock_in
                total_seconds += duration.total_seconds()
            
            # Add current active session if exists
            current_session = self.get_current_session()
            if current_session and current_session.clock_in:
                current_duration = timezone.now() - current_session.clock_in
                total_seconds += current_duration.total_seconds()
            
            # Convert to hours
            return round(total_seconds / 3600, 2)

        except Exception as e:
            logger.error(f"Error calculating cumulative working hours: {str(e)}")
            return 0.0

    def get_shift_duration_hours(self):
        """Calculate expected shift duration in hours based on employee's shift"""
        from datetime import datetime

        shift = self.employee.assigned_shift
        if not shift:
            # Fallback to default 9 hours
            return 9.0

        # Calculate duration from shift start to end time
        start_dt = datetime.combine(self.date, shift.start_time)
        end_dt = datetime.combine(self.date, shift.end_time)

        # Handle overnight shifts
        if end_dt < start_dt:
            from datetime import timedelta

            end_dt += timedelta(days=1)

        duration = (end_dt - start_dt).total_seconds() / 3600
        return duration

    def is_shift_complete(self):
        """Check if employee has worked the full shift duration"""

        if not self.clock_in:
            return False

        # If already clocked out, check actual hours worked
        if self.clock_out:
            worked_hours = (self.clock_out - self.clock_in).total_seconds() / 3600
        else:
            # Currently clocked in, check hours so far
            worked_hours = (timezone.now() - self.clock_in).total_seconds() / 3600

        expected_hours = self.get_shift_duration_hours()

        # Consider shift complete if worked at least 90% of expected hours
        return worked_hours >= (expected_hours * 0.9)

    def should_stop_location_tracking(self):
        """Determine if location tracking should be stopped"""

        if not self.location_tracking_active:
            return False

        # Stop if clocked out
        if self.clock_out:
            return True

        # User requested tracking until actual clock-out, so we ignore location_tracking_end_time for stopping
        # if self.location_tracking_end_time and timezone.now() >= self.location_tracking_end_time:
        #    return True

        return False

    def get_current_session(self):
        """Get the currently active session (not clocked out)"""
        from .models import AttendanceSession

        return (
            AttendanceSession.objects.filter(
                employee=self.employee,
                date=self.date,
                clock_out__isnull=True,
                is_active=True,
            )
            .order_by("-session_number")
            .first()
        )

    def can_clock_in(self):
        """Check if employee can clock in based on current state and session limits"""
        # Cannot clock in if already clocked in
        if self.is_currently_clocked_in:
            return False

        # Cannot clock in if maximum daily sessions reached
        if self.daily_sessions_count >= self.max_daily_sessions:
            return False

        return True


class AttendanceSession(models.Model):
    """Individual clock-in/clock-out sessions within a day"""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_sessions")
    date = models.DateField()
    session_number = models.IntegerField(help_text="Session number for the day (1, 2, 3)")

    # Session timing
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(null=True, blank=True)

    # Location coordinates (matching existing structure)
    clock_in_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    clock_in_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    clock_out_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    clock_out_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    # Session type and status
    SESSION_TYPE_CHOICES = [
        ("WEB", "Web/Office"),
        ("REMOTE", "Remote/WFH"),
    ]
    session_type = models.CharField(max_length=50, choices=SESSION_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    location_validated = models.BooleanField(default=False)

    # Session duration (in minutes to match existing structure)
    duration_minutes = models.IntegerField(default=0, help_text="Duration of this session in minutes")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employees_attendancesession"
        unique_together = [["employee", "date", "session_number"]]
        ordering = ["date", "session_number"]

    def __str__(self):
        return f"{self.employee} - {self.date} - Session {self.session_number} ({self.session_type})"

    @property
    def duration_hours(self):
        """Convert duration from minutes to hours"""
        return round(self.duration_minutes / 60, 2) if self.duration_minutes else 0.0

    def calculate_duration(self):
        """Calculate and update session duration"""
        if self.clock_in and self.clock_out:
            duration = self.clock_out - self.clock_in
            self.duration_minutes = int(duration.total_seconds() / 60)
        else:
            self.duration_minutes = 0
        return self.duration_minutes

    def save(self, *args, **kwargs):
        # Auto-calculate duration on save
        self.calculate_duration()
        super().save(*args, **kwargs)

    def get_location_logs(self):
        """Get all location logs for this session"""
        return self.location_logs.all().order_by("timestamp")

    def get_location_count(self):
        """Get count of location logs for this session"""
        return self.location_logs.count()

    def get_latest_location(self):
        """Get the most recent location for this session"""
        return self.location_logs.first()  # First due to ordering by -timestamp


class SessionLocationLog(models.Model):
    """Location tracking for specific attendance sessions"""

    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="location_logs")
    timestamp = models.DateTimeField(auto_now_add=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy = models.FloatField(null=True, blank=True, help_text="GPS accuracy in meters")

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.session.employee} - Session {self.session.session_number} - {self.timestamp}"


class LocationLog(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="location_logs")
    attendance_session = models.ForeignKey(
        "AttendanceSession",
        on_delete=models.CASCADE,
        related_name="employee_location_logs",  # Changed to avoid conflict
        null=True,
        blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)

    # Tracking metadata
    LOG_TYPE_CHOICES = [
        ("CLOCK_IN", "Clock In"),
        ("CLOCK_OUT", "Clock Out"),
        ("HOURLY", "Hourly Tracking"),
        ("MANUAL", "Manual Update"),
    ]
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, default="MANUAL")
    accuracy = models.FloatField(null=True, blank=True, help_text="GPS accuracy in meters")
    address = models.TextField(null=True, blank=True, help_text="Reverse geocoded address")

    # Tracking status
    is_valid = models.BooleanField(default=True, help_text="Whether this location is valid")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["employee", "timestamp"]),
            models.Index(fields=["attendance_session", "log_type"]),
        ]

    def __str__(self):
        return f"{self.employee} - {self.get_log_type_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class LeaveBalance(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="leave_balance")

    # Leave Allocations
    casual_leave_allocated = models.FloatField(default=12.0, help_text="Total CL allocated per year")
    sick_leave_allocated = models.FloatField(default=12.0, help_text="Total SL allocated per year")

    # Leave Used
    casual_leave_used = models.FloatField(default=0.0)
    sick_leave_used = models.FloatField(default=0.0)
    unpaid_leave = models.FloatField(default=0.0)

    # Carry forward / Lapsed
    carry_forward_leave = models.FloatField(default=0.0, help_text="Leave carried from previous year")
    lapsed_leave = models.FloatField(default=0.0, help_text="Leave that expired")

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def casual_leave_balance(self):
        return max(0, self.casual_leave_allocated - self.casual_leave_used)

    @property
    def sick_leave_balance(self):
        return max(0, self.sick_leave_allocated - self.sick_leave_used)

    def get_available_balance(self, leave_type):
        """Get available balance for a specific leave type"""
        if leave_type == "CL":
            return self.casual_leave_balance
        elif leave_type == "SL":
            return self.sick_leave_balance
        else:
            return 0

    def can_apply_leave(self, leave_type, days_requested):
        """Check if employee can apply for the requested leave"""
        available_balance = self.get_available_balance(leave_type)

        if leave_type == "UL":  # Unpaid Leave (LOP) - always allowed
            return {
                "can_apply": True,
                "available": float("inf"),
                "shortfall": 0,
                "will_be_lop": True,
            }

        # For other leave types, check if there's sufficient balance
        shortfall = max(0, days_requested - available_balance)
        will_be_lop = shortfall > 0

        return {
            "can_apply": True,  # Always allow application, excess will be LOP
            "available": available_balance,
            "shortfall": shortfall,
            "will_be_lop": will_be_lop,
        }

    def apply_leave_deduction(self, leave_type, days_approved):
        """Deduct approved leave from balance"""
        if leave_type == "CL":
            self.casual_leave_used += days_approved
        elif leave_type == "SL":
            self.sick_leave_used += days_approved
        elif leave_type == "UL":
            self.unpaid_leave += days_approved
        # OD (On Duty) and OT (Others) don't affect leave balance

        self.save()

    def validate_and_save(self):
        """Validate leave balance data before saving"""
        # Ensure non-negative allocated leaves
        self.casual_leave_allocated = max(0, self.casual_leave_allocated)
        self.sick_leave_allocated = max(0, self.sick_leave_allocated)
        
        # Ensure non-negative used leaves
        self.casual_leave_used = max(0, self.casual_leave_used)
        self.sick_leave_used = max(0, self.sick_leave_used)
        self.unpaid_leave = max(0, self.unpaid_leave)
        
        # Ensure non-negative carry forward
        self.carry_forward_leave = max(0, self.carry_forward_leave)
        
        self.save()
        return self

    @property
    def total_balance(self):
        return self.casual_leave_balance + self.sick_leave_balance

    @property
    def has_negative_balance(self):
        return self.casual_leave_balance < 0 or self.sick_leave_balance < 0

    def __str__(self):
        return f"Balance: {self.employee.user.get_full_name()}"


class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ("CL", "Casual Leave"),
        ("SL", "Sick Leave"),
        ("UL", "Unpaid Leave (LOP)"),
        ("OD", "On Duty"),
        ("OT", "Others"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]
    DURATION_CHOICES = [
        ("FULL", "Full Day"),
        ("FIRST_HALF", "First Half"),
        ("SECOND_HALF", "Second Half"),
    ]
    APPROVAL_LEVEL_CHOICES = [
        ("MANAGER", "Manager"),
        ("HR", "HR/Admin"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=2, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    duration = models.CharField(max_length=12, choices=DURATION_CHOICES, default="FULL")
    reason = models.TextField(blank=True)
    supporting_document = models.FileField(upload_to="leave_documents/", null=True, blank=True)

    # Status and Approval
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    approval_level = models.CharField(max_length=10, choices=APPROVAL_LEVEL_CHOICES, default="MANAGER")

    # Admin/Manager Actions
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_type = models.CharField(
        max_length=20,
        choices=[
            ("FULL", "Approved (Full Balance)"),
            ("WITH_LOP", "Approved with LOP"),
            ("ONLY_AVAILABLE", "Approved (Only Available Days)"),
        ],
        null=True,
        blank=True,
        help_text="How the leave was approved",
    )
    admin_comment = models.TextField(blank=True, null=True, help_text="Admin/Manager remarks")
    rejection_reason = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def total_days(self):
        """Calculate total leave days"""
        from datetime import datetime

        if self.duration in ["FIRST_HALF", "SECOND_HALF", "HALF"]:  # Include legacy "HALF" option
            return 0.5

        # Helper to convert string to date if needed
        def to_date(date_obj):
            if isinstance(date_obj, str):
                try:
                    return datetime.strptime(date_obj, "%Y-%m-%d").date()
                except ValueError:
                    # Try ISO format
                    try:
                        return datetime.fromisoformat(date_obj).date()
                    except (ValueError, TypeError):
                        logger.debug(
                            "Failed to parse date for leave calculation",
                            date_obj=date_obj,
                        )
                        return None
            elif isinstance(date_obj, datetime):
                return date_obj.date()
            return date_obj

        start = to_date(self.start_date)
        end = to_date(self.end_date)

        if start and end:
            days = (end - start).days + 1
            return float(days)

        # Fallback if conversion fails
        return 1.0

    @property
    def is_negative_balance(self):
        """Check if this leave will result in negative balance"""
        try:
            validation = self.validate_leave_application()
            return validation.get("will_be_lop", False)
        except:
            return False

    def validate_leave_application(self):
        """Validate leave application and return detailed information"""
        try:
            balance = self.employee.leave_balance
            leave_check = balance.can_apply_leave(self.leave_type, self.total_days)

            return {
                "is_valid": leave_check["can_apply"] or self.leave_type == "UL",
                "available_balance": leave_check["available"],
                "requested_days": self.total_days,
                "shortfall": leave_check["shortfall"],
                "will_be_lop": leave_check["will_be_lop"],
                "leave_type_display": self.get_leave_type_display(),
                "message": self._generate_validation_message(leave_check),
            }
        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e),
                "message": "Unable to validate leave application. Please contact HR.",
            }

    def _generate_validation_message(self, leave_check):
        """Generate user-friendly validation message"""
        if self.leave_type == "UL":
            return f"Approving this Unpaid Leave (LOP) application for {self.total_days} days will result in LOP."

        if leave_check["can_apply"]:
            return f"Leave application can be approved. You have {leave_check['available']} days available."
        else:
            available = leave_check["available"]
            shortfall = leave_check["shortfall"]

            if available == 0:
                return f"You don't have any {self.get_leave_type_display()} balance. Approving this leave will result in {self.total_days} days of LOP."
            else:
                return f"You only have {available} days of {self.get_leave_type_display()} available. Approving this leave will result in {shortfall} days of LOP."

    def save(self, *args, **kwargs):
        """Override save to validate leave application"""
        if not self.pk:  # Only validate on creation
            validation = self.validate_leave_application()
            if not validation["is_valid"] and self.leave_type != "UL":
                # Convert to mixed leave (partial paid + LOP) if needed
                pass  # We'll handle this in the view

        super().save(*args, **kwargs)

    def approve_leave(self, approved_by_user, approval_type="FULL"):
        """
        Approve leave and deduct from balance

        Args:
            approved_by_user: User who is approving
            approval_type: 'FULL', 'WITH_LOP', or 'ONLY_AVAILABLE'
        """
        if self.status != "PENDING":
            return False

        # Deduct from leave balance first, then update status
        try:
            balance = self.employee.leave_balance
            validation = self.validate_leave_application()

            if approval_type == "ONLY_AVAILABLE":
                # Approve only available days, don't process LOP
                available = validation["available_balance"]
                if available > 0:
                    balance.apply_leave_deduction(self.leave_type, available)
                # Update the leave request to reflect only approved days
                # Note: This changes the original request
                from datetime import timedelta

                if self.duration == "HALF":
                    # Can't split half day
                    if available >= 0.5:
                        balance.apply_leave_deduction(self.leave_type, 0.5)
                    else:
                        return False  # Can't approve
                else:
                    # Adjust end date to match available days
                    self.end_date = self.start_date + timedelta(days=int(available) - 1)

            elif self.leave_type == "UL" or approval_type == "WITH_LOP":
                # Direct unpaid leave application OR approval with LOP
                if self.leave_type == "UL":
                    balance.apply_leave_deduction("UL", self.total_days)
                elif validation["will_be_lop"]:
                    # Split into paid leave + LOP
                    available = validation["available_balance"]
                    lop_days = validation["shortfall"]

                    # Deduct available balance from requested leave type
                    if available > 0:
                        balance.apply_leave_deduction(self.leave_type, available)

                    # Deduct remaining days as LOP
                    if lop_days > 0:
                        balance.apply_leave_deduction("UL", lop_days)
                else:
                    # Full deduction from requested leave type (sufficient balance)
                    balance.apply_leave_deduction(self.leave_type, self.total_days)
            else:
                # FULL approval - deduct from requested leave type
                if validation["will_be_lop"] and approval_type != "WITH_LOP":
                    # Insufficient balance and not approved with LOP
                    return False
                balance.apply_leave_deduction(self.leave_type, self.total_days)

            # Update status after successful deduction
            self.status = "APPROVED"
            self.approved_by = approved_by_user
            self.approved_at = timezone.now()
            self.approval_type = approval_type
            self.save()

            # Create attendance records for each day of the leave
            from datetime import timedelta

            current_date = self.start_date
            while current_date <= self.end_date:
                # Skip weekends/weekly offs if they exist
                if not self.employee.is_week_off(current_date):
                    # Determine attendance status based on duration
                    if self.duration in ["FIRST_HALF", "SECOND_HALF", "HALF"]:  # Include legacy "HALF" option
                        attendance_status = "HALF_DAY"
                    else:
                        attendance_status = "LEAVE"
                    
                    # Create or update attendance record
                    Attendance.objects.update_or_create(
                        employee=self.employee,
                        date=current_date,
                        defaults={
                            "status": attendance_status,
                            "clock_in": None,
                            "clock_out": None,
                        },
                    )
                current_date += timedelta(days=1)

            return True

        except Exception as e:
            # Don't change status if deduction fails
            logger.error(f"Error approving leave: {e}")
            return False

    def __str__(self):
        return f"{self.get_leave_type_display()} - {self.employee.user.get_full_name()} ({self.start_date} to {self.end_date})"


class Payslip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payslips")
    month = models.DateField(help_text="Select any date in the month")
    pdf_file = models.FileField(upload_to="payslips/", null=True, blank=True)
    
    # Financial Breakdown
    basic = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conveyance_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    special_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_gross = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Deductions
    employee_pf = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employer_pf = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    professional_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Meta info
    worked_days = models.FloatField(default=0)
    total_days = models.IntegerField(default=30)
    
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-month"]

    @property
    def total_deductions(self):
        """Calculate total deductions (Employee PF + Professional Tax)"""
        return self.employee_pf + self.professional_tax

    def __str__(self):
        return f"Payslip - {self.employee.user.get_full_name()} - {self.month.strftime('%b %Y')}"


class HandbookSection(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField(help_text="HTML content is supported")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class PolicySection(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField(help_text="HTML content is supported")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "Policy Sections"

    def __str__(self):
        return self.title


class RegularizationRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="regularization_requests")
    date = models.DateField(help_text="Date to be regularized")
    check_in = models.TimeField(null=True, blank=True, verbose_name="New Check-In Time")
    check_out = models.TimeField(null=True, blank=True, verbose_name="New Check-Out Time")
    reason = models.TextField(help_text="Reason for regularization")

    # Status
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_regularizations",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    manager_comment = models.TextField(blank=True, null=True, verbose_name="Manager Remarks")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Regularization - {self.employee.user.get_full_name()} ({self.date})"


class ExitInitiative(models.Model):
    """
    Model to track employee exit requests with approval workflow
    Supports resignation (with approval), absconding, and termination
    """

    EXIT_TYPE_CHOICES = [
        ("RESIGNATION", "Resignation"),
        ("ABSCONDED", "Absconded"),
        ("TERMINATED", "Terminated"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("COMPLETED", "Completed"),  # Employee has left
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="exit_initiatives")
    exit_type = models.CharField(max_length=20, choices=EXIT_TYPE_CHOICES, help_text="Type of exit")
    submission_date = models.DateField(help_text="Date when exit was initiated")
    exit_note = models.TextField(help_text="Reason for exit")

    # Notice period (for absconding/termination)
    notice_period_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Notice period in days (for absconding/termination)",
    )

    # Last working day
    last_working_day = models.DateField(null=True, blank=True, help_text="Calculated or approved last working day")

    # Approval workflow (for resignations)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        help_text="Status of exit request (mainly for resignations)",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_exits",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True, help_text="Reason for rejection (if applicable)")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Exit Initiative"
        verbose_name_plural = "Exit Initiatives"

    def __str__(self):
        return f"{self.get_exit_type_display()} - {self.employee.user.get_full_name()} ({self.submission_date})"

    def calculate_last_working_day(self):
        """
        Calculate last working day based on exit type
        - For resignation: 2 months from approval date
        - For absconding/termination: submission date + notice period
        """
        from datetime import timedelta

        from dateutil.relativedelta import relativedelta

        if self.exit_type == "RESIGNATION" and self.approved_at:
            # 2 months from approval date
            self.last_working_day = self.approved_at.date() + relativedelta(months=2)
        elif self.exit_type in ["ABSCONDED", "TERMINATED"] and self.notice_period_days:
            # Submission date + notice period
            self.last_working_day = self.submission_date + timedelta(days=self.notice_period_days)

        return self.last_working_day


# Signal to automatically create leave balance for new employees
@receiver(post_save, sender=Employee)
def create_leave_balance(sender, instance, created, **kwargs):
    """Automatically create leave balance when a new employee is created"""
    if created:
        # New employees start with 0 leaves during probation period
        # Leaves will be allocated after probation completion or manually by admin
        LeaveBalance.objects.get_or_create(
            employee=instance,
            defaults={
                "casual_leave_allocated": 0.0,
                "sick_leave_allocated": 0.0,
            },
        )


# Signal to clear cache when leave balance is updated
@receiver(post_save, sender=LeaveBalance)
def invalidate_leave_balance_cache(sender, instance, **kwargs):
    """Clear cached data when leave balance is updated"""
    from django.core.cache import cache
    
    employee = instance.employee
    company = employee.company
    
    # Clear employee-specific cache
    cache_keys_to_clear = [
        f"employee_leave_balance_{employee.id}",
        f"employee_dashboard_data_{employee.id}",
        f"employee_profile_data_{employee.id}",
        f"employee_personal_home_{employee.id}",
        f"leave_config_data_{company.id}",
        f"company_leave_summary_{company.id}",
    ]
    
    for cache_key in cache_keys_to_clear:
        cache.delete(cache_key)
    
    logger.info(f"Cache invalidated for employee {employee.user.get_full_name()} leave balance update")
