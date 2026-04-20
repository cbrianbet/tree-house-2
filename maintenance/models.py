from django.db import models
from django.utils import timezone
from authentication.models import CustomUser
from property.models import Property, Unit


class MaintenanceRequest(models.Model):
    CATEGORY_CHOICES = [
        ('plumbing', 'Plumbing'),
        ('electrical', 'Electrical'),
        ('structural', 'Structural'),
        ('appliance', 'Appliance'),
        ('carpentry', 'Carpentry'),
        ('painting', 'Painting'),
        ('masonry', 'Masonry'),
        ('other', 'Other'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    # Either unit (tenant request) or property only (landlord — common area)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='maintenance_requests')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True, related_name='maintenance_requests')
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='submitted_requests')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    assigned_to = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_maintenance'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.priority.upper()}] {self.title} ({self.status})"


class MaintenanceBid(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='bids')
    artisan = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bids')
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('request', 'artisan')

    def __str__(self):
        return f"Bid by {self.artisan.username} on Request {self.request_id} — {self.status}"


class MaintenanceNote(models.Model):
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='maintenance_notes')
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note by {self.author.username} on Request {self.request_id}"


class MaintenanceImage(models.Model):
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='maintenance_images/')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='maintenance_images')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for Request {self.request_id}"
