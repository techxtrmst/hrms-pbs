from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """Called when Django starts - start the email scheduler service"""
        import os

        # Only start scheduler in main process, not in reloader process
        if os.environ.get("RUN_MAIN") == "true" or os.environ.get("RUN_MAIN") is None:
            try:
                from core.email_scheduler import email_scheduler

                email_scheduler.start()
                print("✅ Birthday/Anniversary email scheduler started automatically")
            except Exception as e:
                print(f"⚠️ Could not start email scheduler: {e}")
