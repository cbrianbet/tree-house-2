from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from .models import SystemMetric, AlertRule, AlertInstance, ImpersonationLog
from .serializers import (
    SystemMetricSerializer, AlertRuleSerializer, AlertInstanceSerializer,
    ImpersonationLogSerializer,
)


def _is_admin(user):
    return user.is_staff


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="List system metrics",
    parameters=[
        OpenApiParameter('metric_type', str, description='Filter by metric type'),
        OpenApiParameter('hours', int, description='Lookback window in hours (default 24)'),
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def metric_list(request):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    hours = int(request.query_params.get('hours', 24))
    since = timezone.now() - timezone.timedelta(hours=hours)
    qs = SystemMetric.objects.filter(recorded_at__gte=since)

    metric_type = request.query_params.get('metric_type')
    if metric_type:
        qs = qs.filter(metric_type=metric_type)

    return Response(SystemMetricSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Alert Rules
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="List alert rules",
)
@extend_schema(
    methods=['POST'],
    summary="Create alert rule",
    examples=[
        OpenApiExample(
            'Create Rule',
            value={
                'name': 'High overdue invoices',
                'description': 'Alert when overdue invoices exceed 10',
                'metric_type': 'overdue_invoice_count',
                'condition': 'gt',
                'threshold_value': '10.00',
                'severity': 'warning',
                'enabled': True,
            },
        )
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def alert_rule_list_create(request):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        rules = AlertRule.objects.all().order_by('-created_at')
        return Response(AlertRuleSerializer(rules, many=True).data)

    serializer = AlertRuleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get alert rule")
@extend_schema(
    methods=['PATCH'],
    summary="Update alert rule",
    examples=[OpenApiExample('Disable rule', value={'enabled': False})],
)
@extend_schema(methods=['DELETE'], summary="Delete alert rule")
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def alert_rule_detail(request, pk):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        rule = AlertRule.objects.get(pk=pk)
    except AlertRule.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(AlertRuleSerializer(rule).data)

    if request.method == 'PATCH':
        serializer = AlertRuleSerializer(rule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    rule.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Alert Instances
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="List alert instances",
    parameters=[
        OpenApiParameter('status', str, description='triggered | acknowledged | resolved'),
        OpenApiParameter('severity', str, description='info | warning | critical'),
        OpenApiParameter('hours', int, description='Lookback window in hours (default 72)'),
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alert_list(request):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    hours = int(request.query_params.get('hours', 72))
    since = timezone.now() - timezone.timedelta(hours=hours)
    qs = AlertInstance.objects.select_related('rule', 'acknowledged_by').filter(
        triggered_at__gte=since
    )

    alert_status = request.query_params.get('status')
    if alert_status:
        qs = qs.filter(status=alert_status)

    severity = request.query_params.get('severity')
    if severity:
        qs = qs.filter(rule__severity=severity)

    return Response(AlertInstanceSerializer(qs, many=True).data)


@extend_schema(methods=['GET'], summary="Get alert instance")
@extend_schema(
    methods=['PATCH'],
    summary="Acknowledge or resolve an alert",
    examples=[
        OpenApiExample(
            'Acknowledge',
            value={'status': 'acknowledged', 'note': 'Investigating'},
        ),
        OpenApiExample(
            'Resolve',
            value={'status': 'resolved', 'note': 'Issue fixed'},
        ),
    ],
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def alert_detail(request, pk):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        instance = AlertInstance.objects.select_related('rule', 'acknowledged_by').get(pk=pk)
    except AlertInstance.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(AlertInstanceSerializer(instance).data)

    new_status = request.data.get('status')
    note = request.data.get('note', '')

    valid_transitions = {
        'triggered': ['acknowledged', 'resolved'],
        'acknowledged': ['resolved'],
        'resolved': [],
    }

    if new_status and new_status not in valid_transitions.get(instance.status, []):
        return Response(
            {'detail': f"Cannot transition from '{instance.status}' to '{new_status}'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()

    if new_status == 'acknowledged':
        instance.status = 'acknowledged'
        instance.acknowledged_by = request.user
        instance.acknowledged_at = now
        if note:
            instance.note = note
        instance.save()

    elif new_status == 'resolved':
        instance.status = 'resolved'
        instance.resolved_at = now
        if note:
            instance.note = note
        if not instance.acknowledged_by:
            instance.acknowledged_by = request.user
            instance.acknowledged_at = now
        instance.save()

    return Response(AlertInstanceSerializer(instance).data)


# ---------------------------------------------------------------------------
# Monitoring Dashboard
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Impersonation Logs
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="List impersonation logs",
    parameters=[
        OpenApiParameter('target_user', int, description='Filter by target user PK'),
        OpenApiParameter('hours', int, description='Lookback window in hours (default 72)'),
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def impersonation_log_list(request):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    hours = int(request.query_params.get('hours', 72))
    since = timezone.now() - timezone.timedelta(hours=hours)
    qs = ImpersonationLog.objects.select_related(
        'admin', 'target_user', 'target_user__role'
    ).filter(timestamp__gte=since)

    target_pk = request.query_params.get('target_user')
    if target_pk:
        qs = qs.filter(target_user__pk=target_pk)

    return Response(ImpersonationLogSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Monitoring Dashboard
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="Monitoring dashboard — health status, active alerts, and latest metrics",
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monitoring_dashboard(request):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    active_alerts = AlertInstance.objects.filter(
        status__in=['triggered', 'acknowledged']
    ).select_related('rule')

    alert_counts = {
        'critical': active_alerts.filter(rule__severity='critical').count(),
        'warning': active_alerts.filter(rule__severity='warning').count(),
        'info': active_alerts.filter(rule__severity='info').count(),
    }

    if alert_counts['critical'] > 0:
        health_status = 'critical'
    elif alert_counts['warning'] > 0:
        health_status = 'warning'
    else:
        health_status = 'healthy'

    # Latest recorded value for each metric type
    metric_types = [
        'overdue_invoice_count', 'monthly_revenue', 'occupancy_rate',
        'open_maintenance_count', 'open_dispute_count',
        'pending_application_count', 'payment_success_rate',
    ]
    latest_metrics = {}
    for mt in metric_types:
        metric = SystemMetric.objects.filter(metric_type=mt).order_by('-recorded_at').first()
        if metric:
            latest_metrics[mt] = {
                'value': str(metric.value),
                'recorded_at': metric.recorded_at,
            }

    # Top 5 active alerts (most recent first)
    top_alerts = AlertInstanceSerializer(
        active_alerts.order_by('-triggered_at')[:5],
        many=True,
    ).data

    # 24-hour trend for key metrics (chronological data points)
    since_24h = timezone.now() - timezone.timedelta(hours=24)
    trends = {}
    for mt in ['overdue_invoice_count', 'monthly_revenue', 'occupancy_rate']:
        points = list(
            SystemMetric.objects.filter(
                metric_type=mt, recorded_at__gte=since_24h
            ).order_by('recorded_at').values('value', 'recorded_at')
        )
        trends[mt] = points

    return Response({
        'health_status': health_status,
        'active_alert_counts': alert_counts,
        'latest_metrics': latest_metrics,
        'top_active_alerts': top_alerts,
        'trends': trends,
    })
