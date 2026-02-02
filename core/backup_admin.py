"""
Admin configuration for backup observability and management.

Provides a dedicated admin interface for:
- Viewing backup job history and status
- Browsing backup snapshots
- Manual backup triggers
- Configuration management
- Real-time status monitoring

Uses django-unfold for modern admin UI.
"""

import subprocess
import uuid
from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Avg, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from .backup_models import BackupConfiguration, BackupJob, BackupSnapshot


class BackupJobStatusFilter(admin.SimpleListFilter):
    """Filter backup jobs by status."""

    title = _("Status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return BackupJob.Status.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class BackupJobTypeFilter(admin.SimpleListFilter):
    """Filter backup jobs by type."""

    title = _("Type")
    parameter_name = "job_type"

    def lookups(self, request, model_admin):
        return BackupJob.JobType.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(job_type=self.value())
        return queryset


class TimeRangeFilter(admin.SimpleListFilter):
    """Filter by time range."""

    title = _("Time Range")
    parameter_name = "time_range"

    def lookups(self, request, model_admin):
        return [
            ("1h", _("Last Hour")),
            ("24h", _("Last 24 Hours")),
            ("7d", _("Last 7 Days")),
            ("30d", _("Last 30 Days")),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "1h":
            return queryset.filter(created_at__gte=now - timedelta(hours=1))
        if self.value() == "24h":
            return queryset.filter(created_at__gte=now - timedelta(hours=24))
        if self.value() == "7d":
            return queryset.filter(created_at__gte=now - timedelta(days=7))
        if self.value() == "30d":
            return queryset.filter(created_at__gte=now - timedelta(days=30))
        return queryset


@admin.register(BackupJob)
class BackupJobAdmin(ModelAdmin):
    """Admin interface for backup jobs."""

    list_display = [
        "job_id_display",
        "job_type_label",
        "status_label",
        "started_at",
        "duration_display",
        "size_display",
        "triggered_by",
    ]
    list_filter = [
        BackupJobStatusFilter,
        BackupJobTypeFilter,
        TimeRangeFilter,
        "encrypted",
    ]
    search_fields = ["job_id", "snapshot_id", "error_message"]
    readonly_fields = [
        "job_id",
        "job_type",
        "status",
        "scheduled_at",
        "started_at",
        "completed_at",
        "duration_seconds",
        "snapshot_id",
        "repository",
        "encrypted",
        "size_bytes",
        "files_count",
        "error_message",
        "triggered_by",
        "triggered_by_user",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]

    # Custom actions
    actions_list = ["trigger_database_backup", "trigger_media_backup"]

    def has_add_permission(self, request):
        """Disable manual creation - jobs are created by backup scripts."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion of old job records."""
        return True

    @display(description=_("Job ID"), ordering="job_id")
    def job_id_display(self, obj):
        """Display job ID with link to detail."""
        return format_html(
            '<code style="font-size: 0.85em;">{}</code>',
            obj.job_id[:12] if obj.job_id else "-",
        )

    @display(
        description=_("Type"),
        ordering="job_type",
        label={
            BackupJob.JobType.DATABASE: "info",
            BackupJob.JobType.MEDIA: "warning",
            BackupJob.JobType.FULL: "success",
            BackupJob.JobType.RESTORE_TEST: "info",
        },
    )
    def job_type_label(self, obj):
        """Display job type with colored label."""
        return obj.job_type

    @display(
        description=_("Status"),
        ordering="status",
        label={
            BackupJob.Status.PENDING: "warning",
            BackupJob.Status.RUNNING: "info",
            BackupJob.Status.SUCCESS: "success",
            BackupJob.Status.FAILED: "danger",
            BackupJob.Status.CANCELLED: "warning",
        },
    )
    def status_label(self, obj):
        """Display status with colored label."""
        return obj.status

    @display(description=_("Duration"))
    def duration_display(self, obj):
        """Display human-readable duration."""
        return obj.duration_display

    @display(description=_("Size"))
    def size_display(self, obj):
        """Display human-readable size."""
        return obj.size_display

    @action(description=_("Trigger Database Backup"), icon="backup")
    def trigger_database_backup(self, request):
        """Manually trigger a database backup."""
        return HttpResponseRedirect(reverse("admin:backup_run", args=["database"]))

    @action(description=_("Trigger Media Backup"), icon="cloud_upload")
    def trigger_media_backup(self, request):
        """Manually trigger a media backup."""
        return HttpResponseRedirect(reverse("admin:backup_run", args=["media"]))

    def get_urls(self):
        """Add custom URLs for backup dashboard and actions."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.backup_dashboard_view),
                name="backup_dashboard",
            ),
            path(
                "run/<str:backup_type>/",
                self.admin_site.admin_view(self.backup_run_view),
                name="backup_run",
            ),
            path(
                "snapshots/<str:backup_type>/",
                self.admin_site.admin_view(self.backup_snapshots_view),
                name="backup_snapshots",
            ),
        ]
        return custom_urls + urls

    def backup_run_view(self, request, backup_type):
        """Execute a backup and return JSON response for API calls or redirect for direct access."""
        is_ajax = (
            request.headers.get("Content-Type") == "application/json"
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        )

        if backup_type not in ["database", "media", "prune"]:
            if is_ajax:
                return JsonResponse({"success": False, "error": f"Invalid backup type: {backup_type}"}, status=400)
            messages.error(request, f"Invalid backup type: {backup_type}")
            return HttpResponseRedirect(reverse("admin:core_backupjob_changelist"))

        # Create a pending job record (except for prune)
        job = None
        if backup_type != "prune":
            job = BackupJob.objects.create(
                job_id=f"manual-{backup_type}-{uuid.uuid4().hex[:8]}",
                job_type=backup_type,
                status=BackupJob.Status.RUNNING,
                triggered_by="admin",
                triggered_by_user=request.user,
                scheduled_at=timezone.now(),
                started_at=timezone.now(),
            )

        try:
            # Trigger backup using shared volume trigger file
            # This approach works without requiring docker socket access
            import os

            trigger_dir = "/var/run/backup-triggers"

            # Ensure trigger directory exists
            os.makedirs(trigger_dir, exist_ok=True)

            # Create trigger file based on backup type
            if backup_type == "prune":
                # Prune is not supported via trigger files yet
                if job:
                    job.status = BackupJob.Status.FAILED
                    job.error_message = "Prune operation not supported via trigger files"
                    job.save()
                msg = "Prune operation not supported. Please run manually."
                if is_ajax:
                    return JsonResponse({"success": False, "error": msg})
                messages.error(request, msg)
                return HttpResponseRedirect(reverse("admin:backup_dashboard"))

            trigger_file = os.path.join(trigger_dir, f"trigger-{backup_type}")

            # Create the trigger file
            with open(trigger_file, "w") as f:
                f.write(f"{timezone.now().isoformat()}\n")
                f.write(f"user={request.user.username}\n")
                f.write(f"job_id={job.job_id if job else 'none'}\n")

            # Update job status to pending (will be picked up by watcher)
            if job:
                job.status = BackupJob.Status.PENDING
                job.save()

            msg = f"{backup_type.title()} backup triggered successfully! It will start within 5 seconds."
            if is_ajax:
                return JsonResponse({"success": True, "message": msg, "job_id": job.job_id if job else None})
            messages.success(request, f"✅ {msg}")

        except PermissionError:
            # Trigger directory not accessible
            if job:
                job.status = BackupJob.Status.FAILED
                job.error_message = "Cannot access trigger directory. Check volume mounts."
                job.save()
            msg = "Cannot trigger backup: permission denied. Check container configuration."
            if is_ajax:
                return JsonResponse({"success": False, "error": msg})
            messages.error(request, f"❌ {msg}")
        except FileNotFoundError:
            # Trigger directory doesn't exist
            if job:
                job.status = BackupJob.Status.FAILED
                job.error_message = "Trigger directory not found. Check volume mounts."
                job.save()
            msg = "Cannot trigger backup: trigger directory not found. Check docker-compose configuration."
            if is_ajax:
                return JsonResponse({"success": False, "error": msg})
            messages.error(request, f"❌ {msg}")
        except Exception as e:
            if job:
                job.status = BackupJob.Status.FAILED
                job.error_message = str(e)[:1000]
                job.save()
            if is_ajax:
                return JsonResponse({"success": False, "error": str(e)[:500]})
            messages.error(request, f"❌ Operation error: {str(e)[:200]}")

        if job:
            return HttpResponseRedirect(reverse("admin:core_backupjob_change", args=[job.pk]))
        return HttpResponseRedirect(reverse("admin:backup_dashboard"))

    def backup_snapshots_view(self, request, backup_type):
        """List snapshots for a repository (API endpoint)."""
        if backup_type not in ["database", "media"]:
            return JsonResponse({"success": False, "error": "Invalid backup type"}, status=400)

        try:
            import json
            import shutil

            docker_compose = shutil.which("docker-compose") or shutil.which("docker")

            if docker_compose and "docker" in docker_compose:
                repo = f"rclone:gdrive:HRMS-Backups/{backup_type}"
                cmd = [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "backup",
                    "restic",
                    "--insecure-no-password",
                    "-r",
                    repo,
                    "snapshots",
                    "--json",
                ]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=60, cwd="/var/www/hrms-pbs-staging"
                )
                if result.returncode == 0:
                    try:
                        snapshots = json.loads(result.stdout) if result.stdout.strip() else []
                    except json.JSONDecodeError:
                        snapshots = []
                    return JsonResponse({"success": True, "snapshots": snapshots, "output": result.stdout})
                else:
                    return JsonResponse(
                        {"success": False, "error": result.stderr, "output": result.stdout + result.stderr}, status=500
                    )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Docker not available. Run on server: docker compose exec backup restic snapshots --json",
                    },
                    status=503,
                )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    def backup_dashboard_view(self, request):
        """Render backup dashboard with statistics."""
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        # Job statistics
        total_jobs = BackupJob.objects.count()
        jobs_24h = BackupJob.objects.filter(created_at__gte=last_24h).count()
        successful_24h = BackupJob.objects.filter(created_at__gte=last_24h, status=BackupJob.Status.SUCCESS).count()
        failed_24h = BackupJob.objects.filter(created_at__gte=last_24h, status=BackupJob.Status.FAILED).count()

        # Success rate
        success_rate_7d = 0
        jobs_7d = BackupJob.objects.filter(
            created_at__gte=last_7d, status__in=[BackupJob.Status.SUCCESS, BackupJob.Status.FAILED]
        )
        if jobs_7d.exists():
            success_count = jobs_7d.filter(status=BackupJob.Status.SUCCESS).count()
            success_rate_7d = (success_count / jobs_7d.count()) * 100

        # Latest jobs by type
        latest_db_job = BackupJob.objects.filter(job_type=BackupJob.JobType.DATABASE).first()
        latest_media_job = BackupJob.objects.filter(job_type=BackupJob.JobType.MEDIA).first()
        latest_restore_test = BackupJob.objects.filter(job_type=BackupJob.JobType.RESTORE_TEST).first()

        # Snapshot counts
        db_snapshots = BackupSnapshot.objects.filter(snapshot_type=BackupSnapshot.SnapshotType.DATABASE).count()
        media_snapshots = BackupSnapshot.objects.filter(snapshot_type=BackupSnapshot.SnapshotType.MEDIA).count()

        # Total backup size
        total_size = BackupSnapshot.objects.aggregate(total=Sum("size_bytes"))["total"] or 0

        # Average duration
        avg_duration = (
            BackupJob.objects.filter(status=BackupJob.Status.SUCCESS, duration_seconds__isnull=False).aggregate(
                avg=Avg("duration_seconds")
            )["avg"]
            or 0
        )

        # Recent jobs for timeline
        recent_jobs = BackupJob.objects.all()[:10]

        context = {
            **self.admin_site.each_context(request),
            "title": _("Backup Dashboard"),
            "stats": {
                "total_jobs": total_jobs,
                "jobs_24h": jobs_24h,
                "successful_24h": successful_24h,
                "failed_24h": failed_24h,
                "success_rate_7d": round(success_rate_7d, 1),
                "db_snapshots": db_snapshots,
                "media_snapshots": media_snapshots,
                "total_size": self._format_size(total_size),
                "avg_duration": self._format_duration(avg_duration),
            },
            "latest": {
                "database": latest_db_job,
                "media": latest_media_job,
                "restore_test": latest_restore_test,
            },
            "recent_jobs": recent_jobs,
            "config": BackupConfiguration.get_config(),
        }

        return TemplateResponse(
            request,
            "admin/core/backupjob/dashboard.html",
            context,
        )

    def _format_size(self, size_bytes):
        """Format bytes to human-readable size."""
        if not size_bytes:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def _format_duration(self, seconds):
        """Format seconds to human-readable duration."""
        if not seconds:
            return "-"
        minutes, secs = divmod(int(seconds), 60)
        if minutes:
            return f"{minutes}m {secs}s"
        return f"{secs}s"


@admin.register(BackupSnapshot)
class BackupSnapshotAdmin(ModelAdmin):
    """Admin interface for backup snapshots."""

    list_display = [
        "snapshot_id_display",
        "snapshot_type_label",
        "created_at",
        "age_display",
        "size_display",
        "retention_reason_display",
    ]
    list_filter = [
        "snapshot_type",
        "retention_reason",
    ]
    search_fields = ["snapshot_id"]
    readonly_fields = [
        "snapshot_id",
        "snapshot_type",
        "created_at",
        "size_bytes",
        "repository",
        "tags",
        "retention_reason",
        "last_synced_at",
    ]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        """Disable manual creation - snapshots are synced from restic."""
        return False

    def has_change_permission(self, request, obj=None):
        """Snapshots are read-only."""
        return False

    @display(description=_("Snapshot ID"))
    def snapshot_id_display(self, obj):
        """Display snapshot ID as code."""
        return format_html(
            '<code style="font-size: 0.85em;">{}</code>',
            obj.snapshot_id,
        )

    @display(
        description=_("Type"),
        ordering="snapshot_type",
        label={
            BackupSnapshot.SnapshotType.DATABASE: "info",
            BackupSnapshot.SnapshotType.MEDIA: "warning",
        },
    )
    def snapshot_type_label(self, obj):
        """Display snapshot type with colored label."""
        return obj.snapshot_type

    @display(description=_("Age"))
    def age_display(self, obj):
        """Display human-readable age."""
        return obj.age_display

    @display(description=_("Size"))
    def size_display(self, obj):
        """Display human-readable size."""
        return obj.size_display

    @display(description=_("Retention"))
    def retention_reason_display(self, obj):
        """Display retention reason."""
        return obj.retention_reason.title() if obj.retention_reason else "-"


@admin.register(BackupConfiguration)
class BackupConfigurationAdmin(ModelAdmin):
    """Admin interface for backup configuration."""

    fieldsets = [
        (
            _("Database Backup Schedule"),
            {
                "fields": [
                    "database_backup_enabled",
                    "database_backup_interval_hours",
                ],
                "description": _("Configure automatic database backup schedule"),
            },
        ),
        (
            _("Media Backup Schedule"),
            {
                "fields": [
                    "media_backup_enabled",
                    "media_backup_hour",
                ],
                "description": _("Configure automatic media backup schedule"),
            },
        ),
        (
            _("Restore Testing"),
            {
                "fields": [
                    "restore_test_enabled",
                    "restore_test_day",
                ],
                "description": _("Configure monthly restore testing"),
            },
        ),
        (
            _("Retention Policy"),
            {
                "fields": [
                    "keep_last",
                    "keep_daily",
                    "keep_weekly",
                    "keep_monthly",
                ],
                "description": _("Configure how long to keep backup snapshots"),
            },
        ),
        (
            _("Notifications"),
            {
                "fields": [
                    "notify_on_success",
                    "notify_on_failure",
                ],
            },
        ),
    ]

    def has_add_permission(self, request):
        """Only one configuration allowed (singleton)."""
        return not BackupConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of configuration."""
        return False

    def changelist_view(self, request, extra_context=None):
        """Redirect to change view since this is a singleton."""
        config = BackupConfiguration.get_config()
        return HttpResponseRedirect(reverse("admin:core_backupconfiguration_change", args=[config.pk]))
