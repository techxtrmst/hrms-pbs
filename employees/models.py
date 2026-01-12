from django.db import models
from django.conf import settings
from django.utils import timezone
from companies.models import Company
from datetime import timedelta


class Employee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="employees"
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinates_user",
    )
    profile_picture = models.ImageField(
        upload_to="employee_avatars/", null=True, blank=True
    )

    # Personal Details
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=True, null=True
    )
    MARITAL_STATUS_CHOICES = [
        ("S", "Single"),
        ("M", "Married"),
        ("D", "Divorced"),
        ("W", "Widowed"),
    ]
    marital_status = models.CharField(
        max_length=1, choices=MARITAL_STATUS_CHOICES, blank=True, null=True
    )
    dob = models.DateField(verbose_name="Date of Birth", null=True, blank=True)
    permanent_address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Legacy field - use EmergencyContact model instead",
    )
    badge_id = models.CharField(
        max_length=20, unique=True, null=True, verbose_name="Employee ID"
    )

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
    ifsc_code = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="IFSC Code"
    )
    uan = models.CharField(max_length=20, blank=True, null=True, verbose_name="UAN")
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
    week_off_tuesday = models.BooleanField(
        default=False, help_text="Tuesday is week-off"
    )
    week_off_wednesday = models.BooleanField(
        default=False, help_text="Wednesday is week-off"
    )
    week_off_thursday = models.BooleanField(
        default=False, help_text="Thursday is week-off"
    )
    week_off_friday = models.BooleanField(default=False, help_text="Friday is week-off")
    week_off_saturday = models.BooleanField(
        default=True, help_text="Saturday is week-off"
    )
    week_off_sunday = models.BooleanField(default=True, help_text="Sunday is week-off")

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
            last_employee = (
                Employee.objects.filter(badge_id__startswith=prefix)
                .order_by("-badge_id")
                .first()
            )

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

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="emergency_contacts"
    )
    name = models.CharField(max_length=100, help_text="Full name of emergency contact")
    phone_number = models.CharField(max_length=15, help_text="Contact phone number")
    relationship = models.CharField(
        max_length=50,
        help_text="Relationship to employee (e.g., Spouse, Parent, Sibling)",
    )
    is_primary = models.BooleanField(
        default=False, help_text="Primary emergency contact"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "created_at"]
        verbose_name = "Emergency Contact"
        verbose_name_plural = "Emergency Contacts"

    def __str__(self):
        return (
            f"{self.name} ({self.relationship}) - {self.employee.user.get_full_name()}"
        )

    def save(self, *args, **kwargs):
        """Ensure only one primary contact per employee"""
        if self.is_primary:
            # Set all other contacts for this employee to non-primary
            EmergencyContact.objects.filter(
                employee=self.employee, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class EmployeeIDProof(models.Model):
    employee = models.OneToOneField(
        Employee, on_delete=models.CASCADE, related_name="id_proofs"
    )
    aadhar_front = models.ImageField(
        upload_to="id_proofs/aadhar/", null=True, blank=True
    )
    aadhar_back = models.ImageField(
        upload_to="id_proofs/aadhar/", null=True, blank=True
    )
    pan_card = models.ImageField(upload_to="id_proofs/pan/", null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ID Proofs - {self.employee.user.get_full_name()}"


class Attendance(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="attendances"
    )
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
    is_late = models.BooleanField(
        default=False, help_text="Marked late based on shift timing"
    )
    late_by_minutes = models.IntegerField(
        default=0, help_text="Minutes late after grace period"
    )

    # Grace Period Logic
    is_grace_used = models.BooleanField(
        default=False, help_text="Logged in late but within grace period"
    )
    is_half_day_late = models.BooleanField(
        default=False, help_text="Marked as Half Day due to late login exceed"
    )

    is_early_departure = models.BooleanField(
        default=False, help_text="Left before shift end time"
    )
    early_departure_minutes = models.IntegerField(
        default=0, help_text="Minutes before shift end"
    )

    # Multiple click handling
    clock_in_attempts = models.IntegerField(
        default=0, help_text="Number of clock-in attempts (max 3)"
    )
    daily_clock_count = models.IntegerField(
        default=0, help_text="Number of valid clock-ins today"
    )
    is_currently_clocked_in = models.BooleanField(
        default=False, help_text="Currently clocked in status"
    )
    max_daily_clocks = models.IntegerField(
        default=3, help_text="Maximum allowed clock-ins per day"
    )

    # Location tracking
    location_tracking_active = models.BooleanField(
        default=False, help_text="Whether location tracking is currently active"
    )
    location_tracking_end_time = models.DateTimeField(
        null=True, blank=True, help_text="When location tracking should stop"
    )
    
    # Session tracking
    daily_sessions_count = models.IntegerField(
        default=0, help_text="Number of sessions today"
    )
    max_daily_sessions = models.IntegerField(
        default=3, help_text="Maximum allowed sessions per day"
    )
    current_session_type = models.CharField(
        max_length=20, null=True, blank=True, help_text="Current session type (WEB/REMOTE)"
    )
    
    # Timezone tracking
    user_timezone = models.CharField(
        max_length=50,
        default="Asia/Kolkata",
        help_text="User's timezone when attendance was recorded",
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
        tz_name = (
            self.employee.location.timezone
            if self.employee.location
            else "Asia/Kolkata"
        )
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
                shift = ShiftSchedule.objects.filter(
                    company=self.employee.company
                ).first()

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
                        self.is_half_day_late = (
                            True  # Using same flag but status might be different?
                        )
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
                self.late_by_minutes = int(
                    (clock_in_dt - grace_end_dt).total_seconds() / 60
                )
                # Usually Late Logic doesn't check grace count, you are just late.
                # But typically Late also implies "missed grace".

    def calculate_early_departure(self):
        """Calculate if employee left early based on location timezone"""
        from datetime import datetime
        import pytz

        if not self.clock_out:
            return

        # Get location timezone
        tz_name = (
            self.employee.location.timezone
            if self.employee.location
            else "Asia/Kolkata"
        )
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
            self.early_departure_minutes = int(
                (threshold_dt - clock_out_dt).total_seconds() / 60
            )
        else:
            self.is_early_departure = False
            self.early_departure_minutes = 0

    @property
    def effective_hours(self):
        if self.clock_in:
            # Use current time if active, otherwise clock_out time
            end_time = self.clock_out if self.clock_out else timezone.now()
            diff = end_time - self.clock_in
            total_seconds = diff.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            return f"{hours}:{minutes:02d}{'+' if not self.clock_out else ''}"
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
        sessions = AttendanceSession.objects.filter(
            employee=self.employee, date=self.date
        ).order_by("session_number")

        completed_sessions = sessions.filter(
            clock_in__isnull=False, clock_out__isnull=False
        )

        active_sessions = sessions.filter(
            clock_in__isnull=False, clock_out__isnull=True
        )

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
            "completion_percentage": round((worked_hours / expected_hours) * 100, 1)
            if expected_hours > 0
            else 0,
            "remaining_hours": max(0, expected_hours - worked_hours),
            "is_shift_complete": worked_hours
            >= expected_hours * 0.9,  # 90% completion threshold
        }

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
        """Get the currently active session for this attendance record"""
        return AttendanceSession.objects.filter(
            employee=self.employee,
            date=self.date,
            clock_out__isnull=True,
            is_active=True,
        ).order_by("-session_number").first()

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

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="attendance_sessions"
    )
    date = models.DateField()
    session_number = models.IntegerField(
        help_text="Session number for the day (1, 2, 3)"
    )

    # Session timing
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(null=True, blank=True)

    # Location coordinates (matching existing structure)
    clock_in_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    clock_in_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    clock_out_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    clock_out_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )

    # Session type and status
    SESSION_TYPE_CHOICES = [
        ("WEB", "Web/Office"),
        ("REMOTE", "Remote/WFH"),
    ]
    session_type = models.CharField(max_length=50, choices=SESSION_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    location_validated = models.BooleanField(default=False)

    # Session duration (in minutes to match existing structure)
    duration_minutes = models.IntegerField(
        default=0, help_text="Duration of this session in minutes"
    )

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

    session = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name="location_logs"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy = models.FloatField(
        null=True, blank=True, help_text="GPS accuracy in meters"
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.session.employee} - Session {self.session.session_number} - {self.timestamp}"


class LocationLog(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="location_logs"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    latitude = models.CharField(max_length=50)
    longitude = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.employee} - {self.timestamp}"


class LeaveBalance(models.Model):
    employee = models.OneToOneField(
        Employee, on_delete=models.CASCADE, related_name="leave_balance"
    )

    # Leave Allocations
    casual_leave_allocated = models.FloatField(
        default=12.0, help_text="Total CL allocated per year"
    )
    sick_leave_allocated = models.FloatField(
        default=12.0, help_text="Total SL allocated per year"
    )
    earned_leave_allocated = models.FloatField(
        default=12.0, help_text="Total EL allocated per year"
    )
    comp_off_allocated = models.FloatField(default=0.0, help_text="Comp off earned")

    # Leave Used
    casual_leave_used = models.FloatField(default=0.0)
    sick_leave_used = models.FloatField(default=0.0)
    earned_leave_used = models.FloatField(default=0.0)
    comp_off_used = models.FloatField(default=0.0)
    unpaid_leave = models.FloatField(default=0.0)

    # Carry forward / Lapsed
    carry_forward_leave = models.FloatField(
        default=0.0, help_text="Leave carried from previous year"
    )
    lapsed_leave = models.FloatField(default=0.0, help_text="Leave that expired")

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def casual_leave_balance(self):
        return self.casual_leave_allocated - self.casual_leave_used

    @property
    def sick_leave_balance(self):
        return self.sick_leave_allocated - self.sick_leave_used

    @property
    def earned_leave_balance(self):
        return self.earned_leave_allocated - self.earned_leave_used

    @property
    def comp_off_balance(self):
        return self.comp_off_allocated - self.comp_off_used

    @property
    def total_balance(self):
        return (
            self.casual_leave_balance
            + self.sick_leave_balance
            + self.earned_leave_balance
            + self.comp_off_balance
        )

    @property
    def has_negative_balance(self):
        return (
            self.casual_leave_balance < 0
            or self.sick_leave_balance < 0
            or self.earned_leave_balance < 0
            or self.comp_off_balance < 0
        )

    def __str__(self):
        return f"Balance: {self.employee.user.get_full_name()}"


class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ("CL", "Casual Leave"),
        ("SL", "Sick Leave"),
        ("EL", "Earned Leave"),
        ("CO", "Comp Off"),
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
        ("HALF", "Half Day"),
    ]
    APPROVAL_LEVEL_CHOICES = [
        ("MANAGER", "Manager"),
        ("HR", "HR/Admin"),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leave_requests"
    )
    leave_type = models.CharField(max_length=2, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    duration = models.CharField(max_length=4, choices=DURATION_CHOICES, default="FULL")
    reason = models.TextField(blank=True)
    supporting_document = models.FileField(
        upload_to="leave_documents/", null=True, blank=True
    )

    # Status and Approval
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    approval_level = models.CharField(
        max_length=10, choices=APPROVAL_LEVEL_CHOICES, default="MANAGER"
    )

    # Admin/Manager Actions
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    admin_comment = models.TextField(
        blank=True, null=True, help_text="Admin/Manager remarks"
    )
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

        if self.duration == "HALF":
            return 0.5

        # Helper to convert string to date if needed
        def to_date(date_obj):
            if isinstance(date_obj, str):
                try:
                    return datetime.strptime(date_obj, "%Y-%m-%d").date()
                except:
                    # Try other formats
                    try:
                        return datetime.fromisoformat(date_obj).date()
                    except:
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
            balance = self.employee.leave_balance
            if self.leave_type == "CL":
                return balance.casual_leave_balance < self.total_days
            elif self.leave_type == "SL":
                return balance.sick_leave_balance < self.total_days
            elif self.leave_type == "EL":
                return balance.earned_leave_balance < self.total_days
            elif self.leave_type == "CO":
                return balance.comp_off_balance < self.total_days
        except:
            return False
        return False

    def __str__(self):
        return f"{self.get_leave_type_display()} - {self.employee.user.get_full_name()} ({self.start_date} to {self.end_date})"


class Payslip(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="payslips"
    )
    month = models.DateField(help_text="Select any date in the month")
    pdf_file = models.FileField(upload_to="payslips/", null=True, blank=True)
    net_salary = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-month"]

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

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="regularization_requests"
    )
    date = models.DateField(help_text="Date to be regularized")
    check_in = models.TimeField(null=True, blank=True, verbose_name="New Check-In Time")
    check_out = models.TimeField(
        null=True, blank=True, verbose_name="New Check-Out Time"
    )
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
    manager_comment = models.TextField(
        blank=True, null=True, verbose_name="Manager Remarks"
    )

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

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="exit_initiatives"
    )
    exit_type = models.CharField(
        max_length=20, choices=EXIT_TYPE_CHOICES, help_text="Type of exit"
    )
    submission_date = models.DateField(help_text="Date when exit was initiated")
    exit_note = models.TextField(help_text="Reason for exit")

    # Notice period (for absconding/termination)
    notice_period_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Notice period in days (for absconding/termination)",
    )

    # Last working day
    last_working_day = models.DateField(
        null=True, blank=True, help_text="Calculated or approved last working day"
    )

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
    rejection_reason = models.TextField(
        blank=True, null=True, help_text="Reason for rejection (if applicable)"
    )

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
            self.last_working_day = self.submission_date + timedelta(
                days=self.notice_period_days
            )

        return self.last_working_day
