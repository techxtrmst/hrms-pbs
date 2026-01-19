from django.db import models
from django.conf import settings
from companies.models import Company, Location
from django.utils import timezone


class PolicySection(models.Model):
    """
    Defines the sections/chapters of a policy (e.g., Leave Policy, HR Policy, Work Culture, etc.)
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="policy_sections"
    )
    title = models.CharField(max_length=200)
    icon = models.CharField(
        max_length=50, blank=True, help_text="Emoji or icon class (e.g., 📘, 🎯, 📋)"
    )
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "title"]
        unique_together = ["company", "title"]
        verbose_name = "Policy Section"
        verbose_name_plural = "Policy Sections"

    def __str__(self):
        return f"{self.company.name} - {self.title}"


class Policy(models.Model):
    """
    Company Policy model with location-based access control.
    Each entity/location can have its own policy.
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="policies"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="policies",
        help_text="Location/Entity this policy belongs to",
    )
    section = models.ForeignKey(
        PolicySection,
        on_delete=models.CASCADE,
        related_name="policy_entries",
        null=True,
        blank=True,
        help_text="Section this content belongs to",
    )

    title = models.CharField(max_length=300)
    subtitle = models.CharField(max_length=500, blank=True)
    content = models.TextField(
        help_text="Main policy content (supports HTML/rich text)"
    )

    # Metadata
    version = models.CharField(
        max_length=50, default="1.0", help_text="Version number of this policy"
    )
    is_published = models.BooleanField(
        default=False, help_text="Only published policies are visible to employees"
    )
    effective_date = models.DateField(
        default=timezone.now, help_text="Date when this policy becomes effective"
    )

    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="policies_created",
        help_text="Admin who created this policy",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="policies_updated",
        help_text="Admin who last updated this policy",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Acknowledgment tracking
    requires_acknowledgment = models.BooleanField(
        default=False, help_text="Employees must acknowledge reading this policy"
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Policy"
        verbose_name_plural = "Policies"
        indexes = [
            models.Index(fields=["company", "location"]),
            models.Index(fields=["is_published", "effective_date"]),
        ]

    def __str__(self):
        return f"{self.location.name} - {self.title} (v{self.version})"

    def get_acknowledgment_count(self):
        """Get count of employees who have acknowledged this policy"""
        return self.acknowledgments.filter(acknowledged=True).count()

    def get_pending_acknowledgment_count(self):
        """Get count of employees who haven't acknowledged yet"""
        from employees.models import Employee

        # Get all active employees at this location
        total_employees = Employee.objects.filter(
            company=self.company, location=self.location, is_active=True
        ).count()
        acknowledged = self.get_acknowledgment_count()
        return total_employees - acknowledged


class PolicyAcknowledgment(models.Model):
    """
    Tracks which employees have read and acknowledged the policy
    """

    policy = models.ForeignKey(
        Policy, on_delete=models.CASCADE, related_name="acknowledgments"
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="policy_acknowledgments",
    )
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        unique_together = ["policy", "employee"]
        ordering = ["-acknowledged_at"]
        verbose_name = "Policy Acknowledgment"
        verbose_name_plural = "Policy Acknowledgments"

    def __str__(self):
        status = "Acknowledged" if self.acknowledged else "Pending"
        return f"{self.employee.user.get_full_name()} - {self.policy.title} ({status})"

    def save(self, *args, **kwargs):
        if self.acknowledged and not self.acknowledged_at:
            self.acknowledged_at = timezone.now()
        super().save(*args, **kwargs)


class PolicyAttachment(models.Model):
    """
    Attachments/documents related to a policy (PDFs, images, etc.)
    """

    policy = models.ForeignKey(
        Policy, on_delete=models.CASCADE, related_name="attachments"
    )
    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to="policy_attachments/%Y/%m/",
        help_text="Upload PDF, images, or other documents",
    )
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Policy Attachment"
        verbose_name_plural = "Policy Attachments"

    def __str__(self):
        return f"{self.policy.title} - {self.title}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            # Extract file type from filename
            import os

            _, ext = os.path.splitext(self.file.name)
            self.file_type = ext.lower()
        super().save(*args, **kwargs)
