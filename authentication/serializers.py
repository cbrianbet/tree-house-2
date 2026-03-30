from dj_rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers
from .models import CustomUser, Role, TenantProfile, LandlordProfile, AgentProfile, ArtisanProfile, NotificationPreference, MovingCompanyProfile

from dj_rest_auth.registration.serializers import RegisterSerializer


class CustomRegisterSerializer(RegisterSerializer):
	phone = serializers.CharField(required=False, allow_blank=True)
	role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), required=False, allow_null=True)
	first_name = serializers.CharField(required=False, allow_blank=True)
	last_name = serializers.CharField(required=False, allow_blank=True)

	def get_cleaned_data(self):
		data = super().get_cleaned_data()
		data['phone'] = self.validated_data.get('phone', '')
		data['role'] = self.validated_data.get('role', None)
		data['first_name'] = self.validated_data.get('first_name', '')
		data['last_name'] = self.validated_data.get('last_name', '')
		return data

	def save(self, request):
		user = super().save(request)
		user.phone = self.validated_data.get('phone', '')
		user.role = self.validated_data.get('role', None)
		user.first_name = self.validated_data.get('first_name', '')
		user.last_name = self.validated_data.get('last_name', '')
		user.save()
		return user


class CustomUserDetailsSerializer(UserDetailsSerializer):

    class Meta(UserDetailsSerializer.Meta):
        fields = UserDetailsSerializer.Meta.fields + \
            ('phone', 'role', 'is_staff', 'first_name', 'last_name',)


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']


class TenantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantProfile
        fields = ['id', 'user', 'national_id', 'emergency_contact_name', 'emergency_contact_phone']


class LandlordProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandlordProfile
        fields = ['id', 'user', 'company_name', 'tax_id', 'verified']


class AgentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentProfile
        fields = ['id', 'user', 'agency_name', 'license_number', 'commission_rate']


class ArtisanProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtisanProfile
        fields = ['id', 'user', 'trade', 'bio', 'rating', 'verified']
        read_only_fields = ['rating']


class MovingCompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovingCompanyProfile
        fields = [
            'id', 'user', 'company_name', 'description', 'phone',
            'address', 'city', 'service_areas', 'base_price', 'price_per_km',
            'is_verified', 'is_active',
        ]
        read_only_fields = ['is_verified']


class AccountUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role']
        read_only_fields = ['id', 'role']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'email_notifications',
            'payment_due_reminder',
            'payment_received',
            'maintenance_updates',
            'new_maintenance_request',
            'new_application',
            'application_status_change',
            'lease_expiry_notice',
            'updated_at',
        ]
        read_only_fields = ['updated_at']
