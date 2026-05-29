import uuid

from django.conf import settings
from django.db import models

from companies.models import Company


class PayrollBatch(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]
    batch_id = models.CharField(max_length=50, unique=True, help_text="Unique identifier (e.g., BATCH-A1B2C3D4)")
    month = models.IntegerField()
    year = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    total_employees = models.IntegerField(default=0)
    processed_employees = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    companies = models.ManyToManyField(Company, related_name="payroll_batches")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Payroll Batches"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.batch_id:
            self.batch_id = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.batch_id} - {self.month}/{self.year} ({self.status})"


class FinanceAuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Finance Audit Logs"
        ordering = ["-timestamp"]

    def __str__(self):
        user_str = self.user.get_full_name() if self.user else "System"
        return f"{user_str} - {self.action} at {self.timestamp}"
