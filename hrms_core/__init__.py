"""
HRMS Core package initialization.

This module ensures the Celery app is loaded when Django starts
so that the @shared_task decorator will use this app.
"""

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ("celery_app",)
