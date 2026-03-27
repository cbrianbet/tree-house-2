from rest_framework import serializers
from .models import Property, Unit, PropertyImage, Lease, PropertyAgent


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ['id', 'name', 'description', 'property_type', 'longitude', 'latitude',
                  'owner', 'created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_by']
        read_only_fields = ['owner', 'created_by', 'updated_by', 'deleted_by']


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'property', 'name', 'floor', 'description', 'is_occupied',
                  'amenities', 'bedrooms', 'bathrooms', 'parking_space', 'parking_slots',
                  'is_public', 'price', 'service_charge', 'security_deposit',
                  'created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_by']
        read_only_fields = ['property', 'created_by', 'updated_by', 'deleted_by']


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ['id', 'property', 'image', 'uploaded_at']
        read_only_fields = ['property']


class LeaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lease
        fields = ['id', 'unit', 'tenant', 'start_date', 'end_date', 'rent_amount', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['unit']


class PropertyAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyAgent
        fields = ['id', 'property', 'agent', 'appointed_by', 'appointed_at']
        read_only_fields = ['property', 'appointed_by', 'appointed_at']
