from django.db import models
from authentication.models import CustomUser
from property.models import Property


class NeighborhoodInsight(models.Model):
    TYPE_SCHOOL = 'school'
    TYPE_HOSPITAL = 'hospital'
    TYPE_SAFETY = 'safety'
    TYPE_TRANSIT = 'transit'
    TYPE_RESTAURANT = 'restaurant'
    TYPE_OTHER = 'other'

    TYPE_CHOICES = [
        (TYPE_SCHOOL, 'School'),
        (TYPE_HOSPITAL, 'Hospital'),
        (TYPE_SAFETY, 'Safety'),
        (TYPE_TRANSIT, 'Transit'),
        (TYPE_RESTAURANT, 'Restaurant'),
        (TYPE_OTHER, 'Other'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='neighborhood_insights')
    insight_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    lat = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)
    lng = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)
    notes = models.TextField(blank=True)
    added_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='added_insights')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"NeighborhoodInsight({self.insight_type}: {self.name} @ {self.property})"
