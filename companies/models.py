from django.db import models


class Company(models.Model):
    """
    Company model for multi-tenant HRMS system
    Each company has isolated data accessible through their domain
    """

    LOCATION_CHOICES = [
        ("INDIA", "India"),
        ("US", "United States"),
        ("BOTH", "India & Dhaka"),
    ]

    name = models.CharField(
        max_length=255, unique=True, help_text="Company name (e.g., Petabytz)"
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    # Domain configuration for multi-tenancy
    primary_domain = models.CharField(
        max_length=255, unique=True, help_text="Primary domain (e.g., petabytz.com)"
    )
    allowed_domains = models.TextField(
        blank=True,
        null=True,
        help_text="Comma-separated list of allowed domains (e.g., petabytz.com,www.petabytz.com)",
    )

    # Location configuration
    location = models.CharField(
        max_length=20,
        choices=LOCATION_CHOICES,
        default="INDIA",
        help_text="Primary location of the company",
    )

    # Company branding
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)

    # Company contact info
    email_domain = models.CharField(
        max_length=255,
        unique=True,
        help_text="Email domain for employees (e.g., petabytz.com for user@petabytz.com)",
    )
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)

    # Address information
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    # Database configuration (for future multi-database support)
    db_schema = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Database schema name for this company",
    )

    currency = models.CharField(
        max_length=10, default="INR", help_text="Currency symbol (e.g., INR, USD)"
    )

    # Email Configuration for Birthday/Anniversary Notifications
    hr_email = models.EmailField(
        blank=True,
        null=True,
        help_text="HR email address for sending birthday/anniversary emails",
    )
    hr_email_password = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Email password or app password (encrypted in production)",
    )
    hr_email_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="HR Team",
        help_text="Display name for HR emails (e.g., 'Petabytz HR')",
    )

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.primary_domain})"

    def get_allowed_domains_list(self):
        """Returns list of allowed domains"""
        if self.allowed_domains:
            return [d.strip() for d in self.allowed_domains.split(",")]
        return [self.primary_domain]

    def is_domain_allowed(self, domain):
        """Check if a domain is allowed for this company"""
        allowed = self.get_allowed_domains_list()
        return domain.lower() in [d.lower() for d in allowed]

    def get_allowed_email_domains_list(self):
        """Returns list of allowed email domains"""
        domains = [d.strip().lower() for d in self.email_domain.split(",")]
        # Also include allowed_domains that look like they could be email domains
        access_domains = self.get_allowed_domains_list()
        for d in access_domains:
            d_lower = d.lower()
            if d_lower not in domains:
                domains.append(d_lower)
        if "bluebix" in self.name.lower() and "bluebixinc.com" not in domains:
            domains.append("bluebixinc.com")
        if "softstandard" in self.name.lower() and "oppora.ai" not in domains:
            domains.append("oppora.ai")
        return domains

    def is_email_domain_allowed(self, email):
        """Check if an email domain is allowed for this company"""
        if not email or "@" not in email:
            return False
        domain = email.split("@")[1].lower()
        allowed_email_domains = self.get_allowed_email_domains_list()
        return domain in allowed_email_domains

    class Meta:
        verbose_name_plural = "Companies"
        indexes = [
            models.Index(fields=["primary_domain"]),
            models.Index(fields=["email_domain"]),
        ]


class Location(models.Model):
    """
    Location model for company-specific regional settings
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="locations"
    )
    name = models.CharField(
        max_length=255, help_text="Location name (e.g., India, US - East, Dhaka)"
    )
    country_code = models.CharField(
        max_length=5, help_text="ISO Country Code (e.g., IN, US, BD)"
    )
    timezone = models.CharField(
        max_length=100, default="Asia/Kolkata", help_text="Timezone for this location"
    )
    currency = models.CharField(
        max_length=10, default="INR", help_text="Currency symbol for this location (e.g., INR, USD)"
    )
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.company.name})"

    class Meta:
        unique_together = ["company", "name"]


class Department(models.Model):
    """
    Company-specific Departments
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["company", "name"]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Designation(models.Model):
    """
    Company-specific Designations
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="designations"
    )
    name = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="designations",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["company", "name"]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Holiday(models.Model):
    """
    Holiday model for managing company holidays with location support
    """

    HOLIDAY_TYPE_CHOICES = [
        ("MANDATORY", "Mandatory Holiday"),
        ("OPTIONAL", "Optional Holiday"),
        ("RESTRICTED", "Restricted Holiday"),
    ]

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="holidays"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="holidays",
        help_text="Location where this holiday applies",
    )
    name = models.CharField(
        max_length=255, help_text="Holiday name (e.g., Diwali, Independence Day)"
    )
    date = models.DateField(help_text="Holiday date")
    holiday_type = models.CharField(
        max_length=20,
        choices=HOLIDAY_TYPE_CHOICES,
        default="MANDATORY",
        help_text="Type of holiday",
    )
    description = models.TextField(
        blank=True, null=True, help_text="Additional details about the holiday"
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this holiday is currently active"
    )

    # Year field for easy filtering
    year = models.IntegerField(help_text="Year of the holiday")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(
        max_length=255, blank=True, null=True, help_text="Admin who created this"
    )

    class Meta:
        ordering = ["date"]
        unique_together = ["company", "name", "date", "location"]
        verbose_name = "Holiday"
        verbose_name_plural = "Holidays"
        indexes = [
            models.Index(fields=["company", "year"]),
            models.Index(fields=["company", "location"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.date.strftime('%d %b %Y')} ({self.location.name})"

    def save(self, *args, **kwargs):
        # Auto-populate year from date
        if self.date:
            self.year = self.date.year
        super().save(*args, **kwargs)


class ShiftTiming(models.Model):
    """
    Model to store company-specific shift timings and breaks.
    """

    company = models.OneToOneField(
        Company, on_delete=models.CASCADE, related_name="shift_timing"
    )
    duration = models.CharField(max_length=100, default="9:00 hrs")
    morning_break = models.CharField(
        max_length=255, default="15mins from 10:45 to 11:00"
    )
    lunch_break = models.CharField(max_length=255, default="45min from 1:00 to 1:45")
    evening_break = models.CharField(max_length=255, default="15mins from 4:00 to 4:30")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Shift Timings - {self.company.name}"


class ShiftSchedule(models.Model):
    """
    Defines shift timings for employees
    """

    SHIFT_TYPE_CHOICES = [
        ("MORNING", "Morning Shift"),
        ("AFTERNOON", "Afternoon Shift"),
        ("NIGHT", "Night Shift"),
    ]

    GRACE_ACTION_CHOICES = [
        ("HALF_DAY", "Mark as Half Day"),
        ("LOP", "Loss of Pay (Full Day)"),
        ("NONE", "No Action (Just Track)"),
    ]

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="shifts"
    )
    name = models.CharField(
        max_length=100, help_text="e.g., Morning Shift, Night Shift, General"
    )
    shift_type = models.CharField(
        max_length=20, choices=SHIFT_TYPE_CHOICES, default="MORNING"
    )
    start_time = models.TimeField(help_text="Shift start time")
    end_time = models.TimeField(help_text="Shift end time")

    # Grace period and late arrival settings
    grace_period_minutes = models.IntegerField(
        default=15, help_text="Grace period in minutes for late arrival"
    )
    allowed_late_logins = models.IntegerField(
        default=5, help_text="Number of allowed late logins per month before reaction"
    )
    grace_exceeded_action = models.CharField(
        max_length=20,
        choices=GRACE_ACTION_CHOICES,
        default="HALF_DAY",
        help_text="Action to take when allowed late logins count is exceeded",
    )

    early_departure_threshold_minutes = models.IntegerField(
        default=15, help_text="Minutes before shift end considered early departure"
    )

    # Break times
    lunch_break_start = models.TimeField(
        null=True, blank=True, help_text="Lunch break start time"
    )
    lunch_break_end = models.TimeField(
        null=True, blank=True, help_text="Lunch break end time"
    )

    # Working days
    monday = models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["company", "name"]

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

    @property
    def working_days_list(self):
        """Returns list of working days"""
        days = []
        if self.monday:
            days.append("Monday")
        if self.tuesday:
            days.append("Tuesday")
        if self.wednesday:
            days.append("Wednesday")
        if self.thursday:
            days.append("Thursday")
        if self.friday:
            days.append("Friday")
        if self.saturday:
            days.append("Saturday")
        if self.sunday:
            days.append("Sunday")
        return days

    def is_working_day(self, date):
        """Check if given date is a working day for this shift"""
        weekday = date.weekday()  # 0=Monday, 6=Sunday
        working_days = [
            self.monday,
            self.tuesday,
            self.wednesday,
            self.thursday,
            self.friday,
            self.saturday,
            self.sunday,
        ]
        return working_days[weekday]

    def get_shift_duration_timedelta(self):
        """Calculate shift duration as timedelta"""
        from datetime import datetime, timedelta

        # Create dummy datetime objects for today
        dummy_date = datetime.now().date()
        start_dt = datetime.combine(dummy_date, self.start_time)
        end_dt = datetime.combine(dummy_date, self.end_time)

        # Handle overnight shifts (end_time < start_time)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        return end_dt - start_dt


class ShiftBreak(models.Model):
    """
    Break times for a specific shift (e.g., Lunch, Tea, Dinner)
    """

    shift = models.ForeignKey(
        ShiftSchedule, on_delete=models.CASCADE, related_name="breaks"
    )
    name = models.CharField(max_length=100, help_text="e.g., Lunch Break, Tea Break")
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.IntegerField(
        help_text="Duration in minutes", blank=True, null=True
    )

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

    def save(self, *args, **kwargs):
        # Auto-calculate duration if not provided
        if self.start_time and self.end_time and not self.duration_minutes:
            # Simple calculation assuming same day
            # If end < start (night shift break crossing midnight), this might need complex handling
            # For now, simplistic approach
            from datetime import datetime

            dummy_date = datetime.now().date()
            start_dt = datetime.combine(dummy_date, self.start_time)
            end_dt = datetime.combine(dummy_date, self.end_time)

            if end_dt < start_dt:
                # Crossed midnight? (e.g. 11pm to 12am)
                # But datetime.time doesn't carry date info.
                # Assuming typical breaks within a shift.
                # If end_time is smaller, it's likely next day in reality, but here we just want duration.
                # Let's just do (24h - start) + end if end < start
                # Or simplier: add 1 day to end_dt
                from datetime import timedelta

                end_dt += timedelta(days=1)

            diff = end_dt - start_dt
            self.duration_minutes = int(diff.total_seconds() / 60)

        super().save(*args, **kwargs)


class Announcement(models.Model):
    """
    Model for company announcements with optional location targeting.
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="announcements"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="announcements",
        help_text="Specific location for this announcement. Leave empty for all locations.",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(
        upload_to="announcements/",
        blank=True,
        null=True,
        help_text="Optional image for the announcement",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class LocationWeekOff(models.Model):
    """
    Defines week-off configuration for a specific location.
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="location_week_offs"
    )
    location = models.OneToOneField(
        Location, on_delete=models.CASCADE, related_name="week_off_config"
    )

    # Week off days (True = Week Off)
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    friday = models.BooleanField(default=False)
    saturday = models.BooleanField(default=True)
    sunday = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Week-Off Config - {self.location.name}"
