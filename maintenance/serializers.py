from rest_framework import serializers
from .models import MaintenanceRequest, MaintenanceBid, MaintenanceNote, MaintenanceImage


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequest
        fields = [
            'id', 'property', 'unit', 'submitted_by', 'title', 'description',
            'category', 'priority', 'status', 'assigned_to', 'resolved_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['submitted_by', 'assigned_to', 'status', 'resolved_at', 'created_at', 'updated_at']


class MaintenanceBidSerializer(serializers.ModelSerializer):
    artisan_name = serializers.SerializerMethodField()
    artisan_rating = serializers.SerializerMethodField()
    artisan_trade = serializers.SerializerMethodField()
    artisan_job_count = serializers.SerializerMethodField()

    class Meta:
        model = MaintenanceBid
        fields = [
            'id', 'request', 'artisan', 'artisan_name', 'artisan_rating',
            'artisan_trade', 'artisan_job_count', 'proposed_price',
            'message', 'status', 'created_at',
        ]
        read_only_fields = ['request', 'artisan', 'status', 'created_at']

    def get_artisan_name(self, obj):
        full_name = f"{obj.artisan.first_name} {obj.artisan.last_name}".strip()
        return full_name or obj.artisan.username

    def get_artisan_rating(self, obj):
        profile = getattr(obj.artisan, 'artisan_profile', None)
        return str(profile.rating) if profile else None

    def get_artisan_trade(self, obj):
        profile = getattr(obj.artisan, 'artisan_profile', None)
        if not profile:
            return None
        return profile.get_trade_display()

    def get_artisan_job_count(self, obj):
        precomputed = getattr(obj, 'artisan_completed_jobs', None)
        if precomputed is not None:
            return precomputed
        return obj.artisan.assigned_maintenance.filter(status='completed').count()


class MaintenanceNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceNote
        fields = ['id', 'request', 'author', 'note', 'created_at']
        read_only_fields = ['request', 'author', 'created_at']


class MaintenanceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceImage
        fields = ['id', 'request', 'image', 'uploaded_by', 'uploaded_at']
        read_only_fields = ['request', 'uploaded_by', 'uploaded_at']


class MaintenanceTimelineEventSerializer(serializers.Serializer):
    event_type = serializers.CharField()
    description = serializers.CharField()
    actor = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
