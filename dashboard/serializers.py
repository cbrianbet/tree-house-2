from rest_framework import serializers
from authentication.models import CustomUser, Role
from .models import RoleChangeLog


class AdminUserSerializer(serializers.ModelSerializer):
    role_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone',
                  'role', 'role_name', 'is_active', 'is_staff', 'date_joined']

    def get_role_name(self, obj):
        return obj.role.name if obj.role else None


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['role', 'is_active']

    def validate_role(self, value):
        return value


class RoleChangeLogSerializer(serializers.ModelSerializer):
    user_username = serializers.SerializerMethodField()
    changed_by_username = serializers.SerializerMethodField()
    old_role_name = serializers.SerializerMethodField()
    new_role_name = serializers.SerializerMethodField()

    class Meta:
        model = RoleChangeLog
        fields = ['id', 'user', 'user_username', 'changed_by', 'changed_by_username',
                  'old_role', 'old_role_name', 'new_role', 'new_role_name',
                  'changed_at', 'reason']

    def get_user_username(self, obj):
        return obj.user.username if obj.user else None

    def get_changed_by_username(self, obj):
        return obj.changed_by.username if obj.changed_by else None

    def get_old_role_name(self, obj):
        return obj.old_role.name if obj.old_role else None

    def get_new_role_name(self, obj):
        return obj.new_role.name if obj.new_role else None
