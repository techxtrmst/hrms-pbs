"""
Backup models for tracking backup jobs and their status.

These models provide observability and manual control over the backup system
through the Django admin interface using Unfold styling.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class BackupJob(models.Model):
    """
    Represents a backup job configuration and its execution history.
    """

    class JobType(models.TextChoices):
        DATABASE = "database", _("Database")
        MEDIA = "media", _("Media Files")
        FULL = "full", _("Full Backup")
        RESTORE_TEST = "restore_test", _("Restore Test")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        RUNNING = "running", _("Running")
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    # Job identification
    job_id = models.CharField(
        max_length=64,
        unique=True,
        help_text=_("Unique identifier for this backup job"),
    )
    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
        default=JobType.DATABASE,
        db_index=True,
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # Timing
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this job was scheduled to run"),
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this job started executing"),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this job finished (success or failure)"),
    )
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("Duration in seconds"),
    )

    # Backup details
    snapshot_id = models.CharField(
        max_length=64,
        blank=True,
        help_text=_("Restic snapshot ID if backup succeeded"),
    )
    repository = models.CharField(
        max_length=255,
        default="rclone:onedrive:HRMS-Backups",
        help_text=_("Restic repository path"),
    )
    encrypted = models.BooleanField(
        default=False,
        help_text=_("Whether this backup is encrypted"),
    )

    # Size tracking
    size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        help_text=_("Size of backup in bytes"),
    )
    files_count = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("Number of files backed up"),
    )

    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text=_("Error message if job failed"),
    )

    # Trigger info
    triggered_by = models.CharField(
        max_length=50,
        default="schedule",
        help_text=_("What triggered this backup (schedule, manual, deploy)"),
    )
    triggered_by_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_backups",
        help_text=_("User who triggered manual backup"),
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Backup Job")
        verbose_name_plural = _("Backup Jobs")
        indexes = [
            models.Index(fields=["job_type", "status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.job_id} ({self.get_job_type_display()}) - {self.get_status_display()}"

    @property
    def is_complete(self):
        return self.status in [self.Status.SUCCESS, self.Status.FAILED, self.Status.CANCELLED]

    @property
    def size_display(self):
        """Human-readable size."""
        if not self.size_bytes:
            return "-"
        size = self.size_bytes
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @property
    def duration_display(self):
        """Human-readable duration."""
        if not self.duration_seconds:
            return "-"
        minutes, seconds = divmod(self.duration_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m {seconds}s"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


class BackupSnapshot(models.Model):
    """
    Represents a restic snapshot stored in the backup repository.
    Synced from restic snapshot list.
    """

    class SnapshotType(models.TextChoices):
        DATABASE = "database", _("Database")
        MEDIA = "media", _("Media Files")

    # Snapshot identification
    snapshot_id = models.CharField(
        max_length=64,
        unique=True,
        help_text=_("Restic snapshot short ID"),
    )
    snapshot_type = models.CharField(
        max_length=20,
        choices=SnapshotType.choices,
        db_index=True,
    )

    # Timing
    created_at = models.DateTimeField(
        help_text=_("When this snapshot was created"),
    )

    # Size
    size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
    )

    # Repository
    repository = models.CharField(
        max_length=255,
        default="rclone:onedrive:HRMS-Backups",
    )

    # Tags from restic
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Restic tags for this snapshot"),
    )

    # Retention info
    retention_reason = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Why this snapshot is kept (latest, daily, weekly, monthly)"),
    )

    # Sync tracking
    last_synced_at = models.DateTimeField(
        auto_now=True,
        help_text=_("When this snapshot was last synced from restic"),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Backup Snapshot")
        verbose_name_plural = _("Backup Snapshots")

    def __str__(self):
        return f"{self.snapshot_id} ({self.get_snapshot_type_display()}) - {self.created_at}"

    @property
    def size_display(self):
        """Human-readable size."""
        if not self.size_bytes:
            return "-"
        size = self.size_bytes
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @property
    def age_display(self):
        """Human-readable age."""
        delta = timezone.now() - self.created_at
        days = delta.days
        if days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                minutes = delta.seconds // 60
                return f"{minutes}m ago"
            return f"{hours}h ago"
        if days == 1:
            return "1 day ago"
        if days < 7:
            return f"{days} days ago"
        if days < 30:
            weeks = days // 7
            return f"{weeks}w ago"
        if days < 365:
            months = days // 30
            return f"{months}mo ago"
        years = days // 365
        return f"{years}y ago"


class BackupConfiguration(models.Model):
    """
    Singleton model for backup configuration settings.
    Editable through Django admin.
    """

    # Schedule settings
    database_backup_enabled = models.BooleanField(
        default=True,
        help_text=_("Enable scheduled database backups"),
    )
    database_backup_interval_hours = models.IntegerField(
        default=3,
        help_text=_("Hours between database backups"),
    )
    media_backup_enabled = models.BooleanField(
        default=True,
        help_text=_("Enable scheduled media backups"),
    )
    media_backup_hour = models.IntegerField(
        default=2,
        help_text=_("Hour of day (0-23) for daily media backup"),
    )
    restore_test_enabled = models.BooleanField(
        default=True,
        help_text=_("Enable monthly restore testing"),
    )
    restore_test_day = models.IntegerField(
        default=1,
        help_text=_("Day of month (1-28) for restore test"),
    )

    # Retention settings
    keep_last = models.IntegerField(
        default=8,
        help_text=_("Keep the last N snapshots"),
    )
    keep_daily = models.IntegerField(
        default=7,
        help_text=_("Keep daily snapshots for N days"),
    )
    keep_weekly = models.IntegerField(
        default=4,
        help_text=_("Keep weekly snapshots for N weeks"),
    )
    keep_monthly = models.IntegerField(
        default=12,
        help_text=_("Keep monthly snapshots for N months"),
    )

    # Notification settings
    notify_on_success = models.BooleanField(
        default=True,
        help_text=_("Send notification on successful backup"),
    )
    notify_on_failure = models.BooleanField(
        default=True,
        help_text=_("Send notification on failed backup"),
    )

    # Repository info (read-only, set via environment)
    repository_database = models.CharField(
        max_length=255,
        default="rclone:onedrive:HRMS-Backups/database",
        editable=False,
    )
    repository_media = models.CharField(
        max_length=255,
        default="rclone:onedrive:HRMS-Backups/media",
        editable=False,
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Backup Configuration")
        verbose_name_plural = _("Backup Configuration")

    def __str__(self):
        return "Backup Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one configuration exists (singleton pattern)
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """Get or create the singleton configuration."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config
