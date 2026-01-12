from django.db import models
from .models import Company


class ShiftSchedule(models.Model):
    """
    Defines shift timings for employees
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="shifts"
    )
    name = models.CharField(
        max_length=100, help_text="e.g., Morning Shift, Night Shift, General"
    )
    start_time = models.TimeField(help_text="Shift start time")
    end_time = models.TimeField(help_text="Shift end time")

    # Grace period and late arrival settings
    grace_period_minutes = models.IntegerField(
        default=15, help_text="Grace period in minutes for late arrival"
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

    def get_shift_duration_hours(self):
        """Calculate total shift duration in hours"""
        from datetime import datetime, timedelta

        # Create datetime objects for calculation
        start_dt = datetime.combine(datetime.today(), self.start_time)
        end_dt = datetime.combine(datetime.today(), self.end_time)

        # Handle overnight shifts
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        duration = (end_dt - start_dt).total_seconds() / 3600
        return duration

    def get_shift_duration_timedelta(self):
        """Return shift duration as timedelta object"""
        from datetime import datetime, timedelta

        start_dt = datetime.combine(datetime.today(), self.start_time)
        end_dt = datetime.combine(datetime.today(), self.end_time)

        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        return end_dt - start_dt
