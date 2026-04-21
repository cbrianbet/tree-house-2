from django.contrib import admin

from .models import (
    Lease,
    LeaseDocument,
    Property,
    PropertyAgent,
    PropertyImage,
    PropertyReview,
    SavedSearch,
    TenantApplication,
    TenantInvitation,
    TenantReview,
    Unit,
)

admin.site.register(Property)
admin.site.register(Unit)
admin.site.register(Lease)
admin.site.register(PropertyImage)
admin.site.register(PropertyAgent)
admin.site.register(TenantApplication)
admin.site.register(LeaseDocument)
admin.site.register(PropertyReview)
admin.site.register(TenantReview)
admin.site.register(SavedSearch)
admin.site.register(TenantInvitation)
