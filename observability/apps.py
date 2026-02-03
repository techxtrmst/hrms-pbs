"""App configuration for observability."""

from django.apps import AppConfig


class ObservabilityConfig(AppConfig):
    """Configuration for the observability app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "observability"
    verbose_name = "Observability & Monitoring"

    def ready(self):
        """Initialize the observability system when Django starts."""
        # Import signal handlers
        from . import signals  # noqa: F401
