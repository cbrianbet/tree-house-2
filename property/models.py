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
