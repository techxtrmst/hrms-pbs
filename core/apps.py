from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """Called when Django starts - start the email scheduler service"""
        import os

        # Import signals to register them
        import core.signals  # noqa: F401

        # Only start scheduler in main process, not in reloader process
        if os.environ.get("RUN_MAIN") == "true" or os.environ.get("RUN_MAIN") is None:
            try:
                from core.email_scheduler import email_scheduler

                email_scheduler.start()
                from loguru import logger

                logger.info("[INFO] Birthday/Anniversary email scheduler started automatically")
            except Exception as e:
                from loguru import logger

                logger.warning(f"[WARN] Could not start email scheduler: {e}")
