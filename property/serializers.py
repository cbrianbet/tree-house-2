from rest_framework import serializers
from .models import Property, Unit, PropertyImage, Lease, PropertyAgent, TenantApplication, LeaseDocument, PropertyReview, TenantReview, SavedSearch


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
                  'is_public', 'price', 'service_charge', 'security_deposit', 'tour_url',
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


class TenantApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantApplication
        fields = ['id', 'unit', 'applicant', 'status', 'message', 'documents', 'reviewed_by', 'reviewed_at', 'created_at']
        read_only_fields = ['applicant', 'status', 'reviewed_by', 'reviewed_at', 'created_at']


class LeaseDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseDocument
        fields = ['id', 'lease', 'document_type', 'title', 'file_url', 'uploaded_by', 'signed_by', 'signed_at', 'created_at']
        read_only_fields = ['id', 'lease', 'uploaded_by', 'signed_by', 'signed_at', 'created_at']


class PropertyReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = PropertyReview
        fields = ['id', 'reviewer', 'reviewer_name', 'property', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer', 'property', 'created_at']

    def get_reviewer_name(self, obj):
        full_name = f"{obj.reviewer.first_name} {obj.reviewer.last_name}".strip()
        return full_name if full_name else obj.reviewer.username


class TenantReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()

    class Meta:
        model = TenantReview
        fields = ['id', 'reviewer', 'reviewer_name', 'tenant', 'tenant_name', 'property', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer', 'property', 'created_at']

    def get_reviewer_name(self, obj):
        full_name = f"{obj.reviewer.first_name} {obj.reviewer.last_name}".strip()
        return full_name if full_name else obj.reviewer.username

    def get_tenant_name(self, obj):
        full_name = f"{obj.tenant.first_name} {obj.tenant.last_name}".strip()
        return full_name if full_name else obj.tenant.username


class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ['id', 'name', 'filters', 'notify_on_match', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
