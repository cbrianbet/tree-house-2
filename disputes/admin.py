from django.contrib import admin

from .models import Dispute, DisputeMessage

admin.site.register(Dispute)
admin.site.register(DisputeMessage)
