from django.db import models

from authentication.models import CustomUser
from property.models import Property, Unit


class Dispute(models.Model):
    DISPUTE_TYPES = [
        ('rent', 'Rent'),
        ('maintenance', 'Maintenance'),
        ('noise', 'Noise'),
        ('lease_terms', 'Lease Terms'),
        ('deposit', 'Deposit'),
        ('damage', 'Damage'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='disputes_created')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='disputes')
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.SET_NULL, related_name='disputes')
    dispute_type = models.CharField(max_length=20, choices=DISPUTE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    title = models.CharField(max_length=200)
    description = models.TextField()
    resolved_by = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='disputes_resolved'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dispute({self.id}: {self.title} [{self.status}])"


class DisputeMessage(models.Model):
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='dispute_messages')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"DisputeMessage from {self.sender.username} on Dispute({self.dispute_id})"
