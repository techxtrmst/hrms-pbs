from django.db import models
from django.conf import settings
from companies.models import Company

class Employee(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee_profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees')
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')
    profile_picture = models.ImageField(upload_to='employee_avatars/', null=True, blank=True)
    
    # Personal Details
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    MARITAL_STATUS_CHOICES = [('S', 'Single'), ('M', 'Married'), ('D', 'Divorced'), ('W', 'Widowed')]
    marital_status = models.CharField(max_length=1, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)
    dob = models.DateField(verbose_name="Date of Birth", null=True, blank=True)
    permanent_address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    badge_id = models.CharField(max_length=20, unique=True, null=True)

    # Job Profile
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    WORK_TYPE_CHOICES = [('FT', 'Full Time'), ('PT', 'Part Time'), ('CT', 'Contract'), ('RM', 'Remote')]
    work_type = models.CharField(max_length=2, choices=WORK_TYPE_CHOICES, default='FT')
    shift = models.CharField(max_length=50, default='General', blank=True) # E.g., "Morning", "Night", "9-6"
    date_of_joining = models.DateField(null=True, blank=True)
    
    # Financial Details
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="IFSC Code")
    uan = models.CharField(max_length=20, blank=True, null=True, verbose_name="UAN")
    pf_enabled = models.BooleanField(default=False, verbose_name="Provident Fund")
    annual_ctc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Annual CTC")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.designation})"

class EmployeeIDProof(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='id_proofs')
    aadhar_front = models.ImageField(upload_to='id_proofs/aadhar/', null=True, blank=True)
    aadhar_back = models.ImageField(upload_to='id_proofs/aadhar/', null=True, blank=True)
    pan_card = models.ImageField(upload_to='id_proofs/pan/', null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ID Proofs - {self.employee.user.get_full_name()}"

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('HALF_DAY', 'Half Day'),
        ('LEAVE', 'On Leave'),
        ('WFH', 'Work From Home'),
        ('ON_DUTY', 'On Duty'),
        ('WEEKLY_OFF', 'Weekly Off'),
        ('HOLIDAY', 'Holiday'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABSENT')
    location_in = models.CharField(max_length=255, null=True, blank=True)  # Lat,Long
    location_out = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return f"{self.employee} - {self.date}"

    @property
    def effective_hours(self):
        if self.clock_in and self.clock_out:
            diff = self.clock_out - self.clock_in
            total_seconds = diff.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            return f"{hours}:{minutes:02d}"
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

class LocationLog(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='location_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    latitude = models.CharField(max_length=50)
    longitude = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.employee} - {self.timestamp}"

class LeaveBalance(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='leave_balance')
    casual_leave = models.FloatField(default=0.0)
    sick_leave = models.FloatField(default=0.0)
    unpaid_leave = models.FloatField(default=0.0) # Track total unpaid taken

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Balance: {self.employee.user.get_full_name()}"

class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ('CL', 'Casual Leave'),
        ('SL', 'Sick Leave'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    rejection_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return f"{self.leave_type} ({self.start_date} to {self.end_date})"

class Payslip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payslips')
    month = models.DateField(help_text="Select any date in the month")
    pdf_file = models.FileField(upload_to='payslips/', null=True, blank=True)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-month']

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
        ordering = ['order']

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
        ordering = ['order']
        verbose_name_plural = "Policy Sections"

    def __str__(self):
        return self.title
