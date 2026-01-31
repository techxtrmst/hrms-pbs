"""
Core admin configuration with Unfold-styled django-celery-beat integration.

This module re-registers django-celery-beat models with Unfold's ModelAdmin
to maintain consistent styling across the admin interface.
"""

from django.contrib import admin
from django_celery_beat.admin import (
    ClockedScheduleAdmin as BaseClockedScheduleAdmin,
)
from django_celery_beat.admin import (
    CrontabScheduleAdmin as BaseCrontabScheduleAdmin,
)
from django_celery_beat.admin import (
    PeriodicTaskAdmin as BasePeriodicTaskAdmin,
)
from django_celery_beat.admin import (
    PeriodicTaskForm,
    TaskSelectWidget,
)
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget

# Unregister default django-celery-beat admin classes
admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)


class UnfoldTaskSelectWidget(UnfoldAdminSelectWidget, TaskSelectWidget):
    """Task select widget with Unfold styling."""

    pass


class UnfoldPeriodicTaskForm(PeriodicTaskForm):
    """Periodic task form with Unfold-styled widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["task"].widget = UnfoldAdminTextInputWidget()
        self.fields["regtask"].widget = UnfoldTaskSelectWidget()


@admin.register(PeriodicTask)
class PeriodicTaskAdmin(BasePeriodicTaskAdmin, ModelAdmin):
    """Periodic Task admin with Unfold styling."""

    form = UnfoldPeriodicTaskForm


@admin.register(IntervalSchedule)
class IntervalScheduleAdmin(ModelAdmin):
    """Interval Schedule admin with Unfold styling."""

    list_display = ("every", "period")
    list_filter = ("period",)


@admin.register(CrontabSchedule)
class CrontabScheduleAdmin(BaseCrontabScheduleAdmin, ModelAdmin):
    """Crontab Schedule admin with Unfold styling."""

    pass


@admin.register(SolarSchedule)
class SolarScheduleAdmin(ModelAdmin):
    """Solar Schedule admin with Unfold styling."""

    list_display = ("event", "latitude", "longitude")
    list_filter = ("event",)


@admin.register(ClockedSchedule)
class ClockedScheduleAdmin(BaseClockedScheduleAdmin, ModelAdmin):
    """Clocked Schedule admin with Unfold styling."""

    pass
