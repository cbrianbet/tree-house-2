from django.core.validators import MinValueValidator, MaxValueValidator
import os
import uuid

from django.db import models

from authentication.models import CustomUser

class Property(models.Model):
	owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
	name = models.CharField(max_length=255)
	description = models.TextField(blank=True)
	longitude = models.FloatField(null=True, blank=True)
	latitude = models.FloatField(null=True, blank=True)
	property_type = models.CharField(max_length=50, choices=[
		('house', 'House'),
		('apartment', 'Apartment'),
		('commercial', 'Commercial'),
		('land', 'Land'),
		('bungalow', 'Bungalow'),
		('duplex', 'Duplex'),
		('townhouse', 'Townhouse'),
		('studio', 'Studio'),
		('cottage', 'Cottage'),
		('penthouse', 'Penthouse'),
		('other', 'Other'),
	])
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_properties')
	updated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='updated_properties')
	deleted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='deleted_properties')

	def __str__(self):
		return self.name


class Unit(models.Model):
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='units')
	name = models.CharField(max_length=100)
	floor = models.CharField(max_length=50, blank=True)
	description = models.TextField(blank=True)
	is_occupied = models.BooleanField(default=False)
	amenities = models.TextField(blank=True)
	bedrooms = models.PositiveIntegerField(default=0)
	bathrooms = models.PositiveIntegerField(default=0)
	parking_space = models.BooleanField(default=False)
	parking_slots = models.PositiveIntegerField(default=0)
	is_public = models.BooleanField(default=False)
	price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	service_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	security_deposit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	tour_url = models.CharField(max_length=500, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_units')
	updated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='updated_units')
	deleted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='deleted_units')

	def __str__(self):
		return f"{self.name} ({self.property.name})"


class Lease(models.Model):
	unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='lease')
	tenant = models.ForeignKey(
		CustomUser, on_delete=models.CASCADE, related_name='leases'
	)
	start_date = models.DateField()
	end_date = models.DateField(null=True, blank=True)
	rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Lease for {self.unit} by {self.tenant}"


class PropertyImage(models.Model):
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
	image = models.ImageField(upload_to='property_images/')
	uploaded_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"Image for {self.property.name}"


class PropertyAgent(models.Model):
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_agents')
	agent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='managed_properties')
	appointed_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='appointed_agents')
	appointed_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('property', 'agent')

	def __str__(self):
		return f"{self.agent.username} manages {self.property.name}"


class TenantApplication(models.Model):
	STATUS_CHOICES = [
		('pending', 'Pending'),
		('approved', 'Approved'),
		('rejected', 'Rejected'),
		('withdrawn', 'Withdrawn'),
	]

	unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='applications')
	applicant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='applications')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
	message = models.TextField(blank=True)
	documents = models.JSONField(default=list, blank=True)
	reviewed_by = models.ForeignKey(
		CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_applications'
	)
	reviewed_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('unit', 'applicant')

	def __str__(self):
		return f"Application by {self.applicant.username} for {self.unit}"


def lease_document_upload_to(instance, filename):
	"""Scoped storage path: lease_documents/<lease_id>/<uuid>.<ext> (non-guessable)."""
	ext = os.path.splitext(filename)[1].lower()
	if ext not in ('.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp'):
		ext = '.bin'
	return f'lease_documents/{instance.lease_id}/{uuid.uuid4().hex}{ext}'


class LeaseDocument(models.Model):
	DOCUMENT_TYPES = [
		('lease_agreement', 'Lease Agreement'),
		('addendum', 'Addendum'),
		('notice', 'Notice'),
		('other', 'Other'),
	]
	lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='documents')
	document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
	title = models.CharField(max_length=200)
	# Legacy: external URL only. New uploads use `file`; API exposes download URL as file_url.
	file_url = models.CharField(max_length=500, blank=True, null=True)
	file = models.FileField(upload_to=lease_document_upload_to, blank=True, null=True)
	uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='uploaded_documents')
	signed_by = models.ForeignKey(
		CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='signed_documents'
	)
	signed_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"LeaseDocument({self.title} — {self.document_type})"

	def delete(self, *args, **kwargs):
		if self.file:
			self.file.delete(save=False)
		super().delete(*args, **kwargs)


class PropertyReview(models.Model):
	reviewer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='property_reviews')
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
	rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
	comment = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('reviewer', 'property')

	def __str__(self):
		return f"PropertyReview({self.reviewer.username} → {self.property.name}: {self.rating}/5)"


class TenantReview(models.Model):
	reviewer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tenant_reviews_given')
	tenant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tenant_reviews_received')
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='tenant_reviews')
	rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
	comment = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('reviewer', 'tenant', 'property')

	def __str__(self):
		return f"TenantReview({self.reviewer.username} → {self.tenant.username}: {self.rating}/5)"


class SavedSearch(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='saved_searches')
    name = models.CharField(max_length=200)
    filters = models.JSONField(default=dict)
    notify_on_match = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.name}"


class TenantInvitation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='tenant_invitations')
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    invited_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='sent_tenant_invitations'
    )
    token_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_user = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='accepted_tenant_invitations'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['unit', 'email'],
                condition=models.Q(status='pending'),
                name='property_tenantinvitation_unit_email_pending_uniq',
            ),
        ]

    def __str__(self):
        return f"TenantInvitation({self.email} → {self.unit})"
