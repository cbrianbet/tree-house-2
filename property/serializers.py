from rest_framework import serializers
from .models import (
    Property,
    Unit,
    PropertyImage,
    Lease,
    PropertyAgent,
    TenantApplication,
    LeaseDocument,
    PropertyReview,
    TenantReview,
    SavedSearch,
    TenantInvitation,
)


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


class TenantInvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.CharField(required=False, allow_blank=True, default='')
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    rent_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class TenantInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantInvitation
        fields = [
            'id',
            'unit',
            'email',
            'phone',
            'first_name',
            'last_name',
            'start_date',
            'end_date',
            'rent_amount',
            'invited_by',
            'status',
            'expires_at',
            'accepted_at',
            'accepted_user',
            'created_at',
        ]
        read_only_fields = fields


class TenantInvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    phone = serializers.CharField(required=False, allow_blank=True, default='')
    national_id = serializers.CharField(required=False, allow_blank=True, default='')
    emergency_contact_name = serializers.CharField(required=False, allow_blank=True, default='')
    emergency_contact_phone = serializers.CharField(required=False, allow_blank=True, default='')
