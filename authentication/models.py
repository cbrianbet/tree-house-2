from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    ADMIN = 'Admin'
    LANDLORD = 'Landlord'
    AGENT = 'Agent'
    TENANT = 'Tenant'
    ARTISAN = 'Artisan'
    MOVING_COMPANY = 'MovingCompany'

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=False)


class TenantProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='tenant_profile')
    national_id = models.CharField(max_length=50, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"TenantProfile({self.user.username})"


class LandlordProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='landlord_profile')
    company_name = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"LandlordProfile({self.user.username})"


class AgentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='agent_profile')
    agency_name = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"AgentProfile({self.user.username})"


class NotificationPreference(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_preferences')
    email_notifications = models.BooleanField(default=True)
    # Billing events
    payment_due_reminder = models.BooleanField(default=True)
    payment_received = models.BooleanField(default=True)
    # Maintenance events
    maintenance_updates = models.BooleanField(default=True)
    new_maintenance_request = models.BooleanField(default=True)
    # Application / lease events
    new_application = models.BooleanField(default=True)
    application_status_change = models.BooleanField(default=True)
    lease_expiry_notice = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"NotificationPreference({self.user.username})"


class ArtisanProfile(models.Model):
    TRADE_CHOICES = [
        ('plumbing', 'Plumbing'),
        ('electrical', 'Electrical'),
        ('carpentry', 'Carpentry'),
        ('painting', 'Painting'),
        ('masonry', 'Masonry'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='artisan_profile')
    trade = models.CharField(max_length=50, choices=TRADE_CHOICES)
    bio = models.TextField(blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"ArtisanProfile({self.user.username} — {self.trade})"


class MovingCompanyProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='moving_company_profile')
    company_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    service_areas = models.JSONField(default=list, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_per_km = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"MovingCompanyProfile({self.user.username} — {self.company_name})"
