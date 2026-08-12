from django.contrib import admin

from .models import AnalyticsDailyMetric, AnalyticsEvent, MLModelArtifact, UserSession


class ReadOnlyAnalyticsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(ReadOnlyAnalyticsAdmin):
    list_display = ['event_type', 'user', 'product', 'market', 'order', 'occurred_at']
    list_filter = ['event_type', 'occurred_at']
    date_hierarchy = 'occurred_at'


@admin.register(UserSession)
class UserSessionAdmin(ReadOnlyAnalyticsAdmin):
    list_display = ['user', 'session_key', 'started_at', 'ended_at', 'duration', 'is_active']
    list_filter = ['is_active', 'device_type']


@admin.register(AnalyticsDailyMetric)
class AnalyticsDailyMetricAdmin(ReadOnlyAnalyticsAdmin):
    list_display = ['date', 'scope', 'market', 'product', 'paid_orders', 'units_sold', 'gross_revenue']
    list_filter = ['scope', 'date']


@admin.register(MLModelArtifact)
class MLModelArtifactAdmin(ReadOnlyAnalyticsAdmin):
    list_display = ['model_type', 'version', 'sample_count', 'is_active', 'training_ended_at']
    list_filter = ['model_type', 'is_active']
