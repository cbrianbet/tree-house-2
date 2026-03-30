from django.db import models
from authentication.models import CustomUser, MovingCompanyProfile


class MovingBooking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    company = models.ForeignKey(MovingCompanyProfile, on_delete=models.CASCADE, related_name='bookings')
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='moving_bookings')
    moving_date = models.DateField()
    moving_time = models.TimeField()
    pickup_address = models.CharField(max_length=255)
    delivery_address = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MovingBooking({self.customer.username} → {self.company.company_name} on {self.moving_date})"


class MovingCompanyReview(models.Model):
    company = models.ForeignKey(MovingCompanyProfile, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='moving_reviews')
    booking = models.ForeignKey(MovingBooking, on_delete=models.SET_NULL, null=True, blank=True, related_name='review')
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'reviewer')

    def __str__(self):
        return f"MovingCompanyReview({self.reviewer.username} → {self.company.company_name}, {self.rating}/5)"
