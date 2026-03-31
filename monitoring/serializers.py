from rest_framework import serializers
from .models import SystemMetric, AlertRule, AlertInstance, ImpersonationLog


class SystemMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemMetric
        fields = ['id', 'metric_type', 'value', 'recorded_at']


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'description', 'metric_type', 'condition',
            'threshold_value', 'severity', 'enabled', 'created_by', 'created_at',
        ]
        read_only_fields = ['created_by', 'created_at']


class AlertInstanceSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    rule_severity = serializers.CharField(source='rule.severity', read_only=True)
    rule_metric_type = serializers.CharField(source='rule.metric_type', read_only=True)
    acknowledged_by_username = serializers.SerializerMethodField()

    class Meta:
        model = AlertInstance
        fields = [
            'id', 'rule', 'rule_name', 'rule_severity', 'rule_metric_type',
            'status', 'triggered_at', 'triggered_value',
            'acknowledged_by', 'acknowledged_by_username', 'acknowledged_at',
            'resolved_at', 'note',
        ]
        read_only_fields = [
            'rule', 'triggered_at', 'triggered_value',
            'acknowledged_by', 'acknowledged_at', 'resolved_at',
        ]

    def get_acknowledged_by_username(self, obj):
        if obj.acknowledged_by:
            return obj.acknowledged_by.username
        return None


class ImpersonationLogSerializer(serializers.ModelSerializer):
    admin_username = serializers.CharField(source='admin.username', read_only=True)
    target_username = serializers.CharField(source='target_user.username', read_only=True)
    target_role = serializers.SerializerMethodField()

    class Meta:
        model = ImpersonationLog
        fields = [
            'id', 'admin', 'admin_username',
            'target_user', 'target_username', 'target_role',
            'path', 'method', 'timestamp',
        ]

    def get_target_role(self, obj):
        if obj.target_user.role:
            return obj.target_user.role.name
        return None
