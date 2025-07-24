from dj_rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers
from .models import Role

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
