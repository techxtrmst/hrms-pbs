from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.user.username}"


class Notification(models.Model):
    """
    Model to track notifications for admins and managers
    """

    NOTIFICATION_TYPES = [
        ("LEAVE_REQUEST", "Leave Request"),
        ("REGULARIZATION_REQUEST", "Regularization Request"),
        ("SHIFT_CHANGE", "Shift Change"),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    message = models.TextField()

    # Generic relation to link to LeaveRequest or RegularizationRequest
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.notification_type} for {self.recipient.username}"


class GlobalConfiguration(models.Model):
    """
    Singleton model for global system configuration
    """

    default_language = models.CharField(max_length=10, default="en")
    default_currency = models.CharField(max_length=10, default="INR")
    date_format = models.CharField(max_length=20, default="DD-MM-YYYY")

    # Security
    enforce_2fa = models.BooleanField(default=True)
    session_timeout = models.IntegerField(default=30, help_text="Session timeout in minutes")

    # Modules
    module_employee_mgmt = models.BooleanField(default=True)
    module_attendance = models.BooleanField(default=True)
    module_payroll = models.BooleanField(default=True)
    module_ai = models.BooleanField(default=True)

    # Environment
    is_maintenance_mode = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1  # Ensure singleton
        super(GlobalConfiguration, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Global Configuration"


class ApprovalWorkflow(models.Model):
    """
    Model to define multi-level approval workflows
    """

    WORKFLOW_TYPES = [
        ("LEAVE", "Leave Request"),
        ("ATTENDANCE", "Attendance Regularization"),
        ("EXPENSE", "Expense Claim"),
        ("ASSET", "Asset Request"),
    ]

    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="workflows")
    workflow_type = models.CharField(max_length=50, choices=WORKFLOW_TYPES)
    name = models.CharField(max_length=100)

    # JSON field or multiple levels
    levels = models.PositiveIntegerField(default=1, help_text="Number of approval levels")

    # Configuration (JSON) to store who is in each level (Role based or User based)
    levels_config = models.JSONField(
        default=dict, help_text='e.g. {"1": {"role": "MANAGER"}, "2": {"role": "COMPANY_ADMIN"}}'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.company.name}"
