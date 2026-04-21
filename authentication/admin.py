from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    AgentProfile,
    ArtisanProfile,
    CustomUser,
    LandlordProfile,
    MovingCompanyProfile,
    NotificationPreference,
    Role,
    TenantProfile,
)


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (*BaseUserAdmin.list_display, 'role', 'phone')
    list_filter = (*BaseUserAdmin.list_filter, 'role')
    search_fields = (*BaseUserAdmin.search_fields, 'phone')
    fieldsets = BaseUserAdmin.fieldsets + (('Profile', {'fields': ('phone', 'role')}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + ((None, {'fields': ('phone', 'role')}),)


admin.site.register(Role)
admin.site.register(TenantProfile)
admin.site.register(LandlordProfile)
admin.site.register(AgentProfile)
admin.site.register(NotificationPreference)
admin.site.register(ArtisanProfile)
admin.site.register(MovingCompanyProfile)
