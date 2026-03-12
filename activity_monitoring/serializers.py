from rest_framework import serializers

from .models import AppActivity, BrowserActivity, SystemEvent


class AppActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AppActivity
        fields = ["app_name", "window_title", "start_time", "end_time", "duration", "is_productive", "category"]


class BrowserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = BrowserActivity
        fields = ["url", "title", "search_query", "timestamp", "time_spent"]


class SystemEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemEvent
        fields = ["event_type", "description", "metadata", "timestamp"]


class ActivityBatchSerializer(serializers.Serializer):
    """
    Handles batched activity data from the agent for smoothness.
    """

    app_activities = AppActivitySerializer(many=True, required=False)
    browser_activities = BrowserActivitySerializer(many=True, required=False)
    system_events = SystemEventSerializer(many=True, required=False)
    is_idle = serializers.BooleanField(default=False)
    idle_seconds = serializers.IntegerField(default=0)
