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


class BankAccount(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    branch_name = models.CharField(max_length=255)
    ifsc_code = models.CharField(max_length=50)
    currency = models.CharField(max_length=10, default="USD")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"


class PurchaseRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    raised_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchase_requests")
    item_name = models.CharField(max_length=255)
    description = models.TextField()
    estimated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_comment = models.TextField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_purchases"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.item_name} - {self.status}"


class Transaction(models.Model):
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("pending_review", "Pending Review"),
        ("flagged", "Flagged"),
    ]
    TRANSACTION_TYPES = [
        ("debit", "Debit (Expense)"),
        ("credit", "Credit (Deposit)"),
    ]
    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.SET_NULL, null=True, blank=True)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, blank=True)
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default="debit")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    screenshot = models.FileField(upload_to="finance/screenshots/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_review")
    mismatch_reason = models.TextField(null=True, blank=True)
    proof_path = models.FileField(upload_to="finance/proofs/", null=True, blank=True)
    statement_path = models.FileField(upload_to="finance/statements/", null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submitted_transactions"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_transactions"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"TX-{self.transaction_id or self.id} ({self.amount})"


class BankStatement(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("reconciled", "Reconciled"),
        ("flagged", "Flagged"),
    ]
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    statement_file = models.FileField(upload_to="finance/statements/")
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Statement for {self.bank_account} uploaded at {self.uploaded_at}"


class ReconciliationResult(models.Model):
    MATCH_CHOICES = [
        ("matched", "Matched"),
        ("unrecognized", "Unrecognized"),
        ("mismatch", "Mismatch"),
    ]
    bank_statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name="reconciliation_results")
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    statement_entry_date = models.DateField()
    statement_entry_amount = models.DecimalField(max_digits=15, decimal_places=2)
    statement_entry_description = models.TextField()
    match_status = models.CharField(max_length=20, choices=MATCH_CHOICES, default="unrecognized")
    explanation = models.TextField(null=True, blank=True)
    raw_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.match_status} - {self.statement_entry_amount} on {self.statement_entry_date}"
