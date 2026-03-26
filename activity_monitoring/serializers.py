from rest_framework import serializers

from .models import AppActivity, BrowserActivity, SystemEvent


class AppActivitySerializer(serializers.ModelSerializer):
    window_title = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    category = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    duration = serializers.DurationField(required=False)
    is_productive = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = AppActivity
        fields = ["app_name", "window_title", "start_time", "end_time", "duration", "is_productive", "category"]


class BrowserActivitySerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    search_query = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    time_spent = serializers.DurationField(required=False)

    class Meta:
        model = BrowserActivity
        fields = ["url", "title", "search_query", "timestamp", "time_spent"]


class SystemEventSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    metadata = serializers.JSONField(required=False)

    class Meta:
        model = SystemEvent
        fields = ["event_type", "description", "metadata", "timestamp"]


class ActivityScreenshotSerializer(serializers.Serializer):
    image_base64 = serializers.CharField()
    timestamp = serializers.DateTimeField(required=False)
    window_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ActivityBatchSerializer(serializers.Serializer):
    """
    Handles batched activity data from the agent for smoothness.
    """

    app_activities = AppActivitySerializer(many=True, required=False)
    browser_activities = BrowserActivitySerializer(many=True, required=False)
    system_events = SystemEventSerializer(many=True, required=False)
    screenshots = ActivityScreenshotSerializer(many=True, required=False)
    is_idle = serializers.BooleanField(default=False)
    idle_seconds = serializers.IntegerField(default=0)
