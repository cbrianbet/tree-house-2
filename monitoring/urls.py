from django.urls import path
from . import views

urlpatterns = [
    path('metrics/', views.metric_list, name='monitoring-metric-list'),
    path('alert-rules/', views.alert_rule_list_create, name='monitoring-alert-rule-list'),
    path('alert-rules/<int:pk>/', views.alert_rule_detail, name='monitoring-alert-rule-detail'),
    path('alerts/', views.alert_list, name='monitoring-alert-list'),
    path('alerts/<int:pk>/', views.alert_detail, name='monitoring-alert-detail'),
    path('dashboard/', views.monitoring_dashboard, name='monitoring-dashboard'),
]
