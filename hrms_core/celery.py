"""
Celery configuration for HRMS PBS project.

This module configures Celery for asynchronous task processing and
periodic task scheduling using django-celery-beat.

Usage:
    Start worker: celery -A hrms_core worker -l info
    Start beat: celery -A hrms_core beat -l info
    Combined (dev only): celery -A hrms_core worker --beat -l info
"""

import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hrms_core.settings")

app = Celery("hrms_core")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
