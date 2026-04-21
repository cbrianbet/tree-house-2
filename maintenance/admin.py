from django.contrib import admin

from .models import MaintenanceBid, MaintenanceImage, MaintenanceNote, MaintenanceRequest

admin.site.register(MaintenanceRequest)
admin.site.register(MaintenanceBid)
admin.site.register(MaintenanceNote)
admin.site.register(MaintenanceImage)
