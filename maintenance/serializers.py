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
    class Meta:
        model = MaintenanceBid
        fields = ['id', 'request', 'artisan', 'proposed_price', 'message', 'status', 'created_at']
        read_only_fields = ['request', 'artisan', 'status', 'created_at']


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
