from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.urls import reverse
from rest_framework import serializers
from .lease_document_validators import validate_lease_document_upload
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


class LeasePartialUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lease
        fields = ['start_date', 'end_date', 'rent_amount', 'is_active']
        extra_kwargs = {
            'start_date': {'required': False},
            'end_date': {'required': False},
            'rent_amount': {'required': False},
            'is_active': {'required': False},
        }


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
    """Create with multipart `file` (preferred) or JSON `file_url` (legacy)."""

    file = serializers.FileField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = LeaseDocument
        fields = [
            'id', 'lease', 'document_type', 'title', 'file_url', 'file',
            'uploaded_by', 'signed_by', 'signed_at', 'created_at',
        ]
        read_only_fields = ['id', 'lease', 'uploaded_by', 'signed_by', 'signed_at', 'created_at']
        extra_kwargs = {
            'file_url': {'required': False, 'allow_null': True, 'allow_blank': True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if instance.file:
            rel = reverse(
                'lease-document-download',
                kwargs={'lease_id': instance.lease_id, 'doc_id': instance.pk},
            )
            data['file_url'] = request.build_absolute_uri(rel) if request else rel
        elif data.get('file_url') is None:
            data['file_url'] = ''
        return data

    def validate_file(self, value):
        if value is None:
            return value
        try:
            validate_lease_document_upload(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_file_url(self, value):
        if value in (None, ''):
            return value
        validator = URLValidator()
        try:
            validator(value)
        except DjangoValidationError:
            raise serializers.ValidationError('Enter a valid URL.')
        return value

    def validate(self, attrs):
        if self.instance is None:
            f = attrs.get('file')
            url = attrs.get('file_url')
            if not f and not url:
                raise serializers.ValidationError(
                    'Provide either file (multipart upload) or file_url (legacy JSON with a pre-hosted URL).',
                )
            if f and url:
                raise serializers.ValidationError('Provide only one of file or file_url.')
            return attrs

        if self.instance.file and attrs.get('file_url'):
            raise serializers.ValidationError(
                'This document is stored on the server; send a new file to replace it, or clear file_url.',
            )
        return attrs

    def create(self, validated_data):
        file = validated_data.pop('file', None)
        if file:
            validated_data['file'] = file
            validated_data['file_url'] = None
        return super().create(validated_data)

    def update(self, instance, validated_data):
        new_file = validated_data.pop('file', None)
        if new_file is not None:
            if instance.file:
                instance.file.delete(save=False)
            validated_data['file'] = new_file
            validated_data['file_url'] = None
        return super().update(instance, validated_data)


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
