from django.contrib import admin

from .models import AlertInstance, AlertRule, ImpersonationLog, SystemMetric

admin.site.register(SystemMetric)
admin.site.register(AlertRule)
admin.site.register(AlertInstance)
admin.site.register(ImpersonationLog)
