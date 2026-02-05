from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """Called when Django starts - start the email scheduler service"""
        import os

        # Only start scheduler in main process, not in reloader process
        # In runserver, RUN_MAIN is 'true' only in the worker process.
        # In production (gunicorn/etc), RUN_MAIN is usually not set.
        import sys

        # Import signals to register them
        import core.signals  # noqa: F401

        if os.environ.get("RUN_MAIN") == "true" or (os.environ.get("RUN_MAIN") is None and "runserver" not in sys.argv):
            try:
                from core.email_scheduler import email_scheduler

                email_scheduler.start()
                from loguru import logger

                logger.info("[INFO] Birthday/Anniversary email scheduler started automatically")
            except Exception as e:
                from loguru import logger

                logger.warning(f"[WARN] Could not start email scheduler: {e}")
