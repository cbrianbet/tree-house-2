from rest_framework import serializers
from authentication.models import MovingCompanyProfile
from .models import MovingBooking, MovingCompanyReview


class MovingBookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = MovingBooking
        fields = [
            'id', 'company', 'customer', 'customer_name',
            'moving_date', 'moving_time', 'pickup_address', 'delivery_address',
            'status', 'estimated_price', 'notes', 'created_at',
        ]
        read_only_fields = ['customer', 'created_at']

    def get_customer_name(self, obj):
        u = obj.customer
        full = f"{u.first_name} {u.last_name}".strip()
        return full or u.username


class MovingCompanyReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = MovingCompanyReview
        fields = ['id', 'company', 'reviewer', 'reviewer_name', 'booking', 'rating', 'comment', 'created_at']
        read_only_fields = ['company', 'reviewer', 'created_at']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def get_reviewer_name(self, obj):
        u = obj.reviewer
        full = f"{u.first_name} {u.last_name}".strip()
        return full or u.username


class MovingCompanyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for directory listing — includes computed avg rating."""
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = MovingCompanyProfile
        fields = [
            'id', 'user', 'company_name', 'description', 'phone',
            'city', 'service_areas', 'base_price', 'price_per_km',
            'is_verified', 'is_active', 'average_rating', 'review_count',
        ]

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 2)

    def get_review_count(self, obj):
        return obj.reviews.count()
