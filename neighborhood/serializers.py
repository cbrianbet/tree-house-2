from rest_framework import serializers
from .models import NeighborhoodInsight


class NeighborhoodInsightSerializer(serializers.ModelSerializer):
    added_by_name = serializers.SerializerMethodField()

    class Meta:
        model = NeighborhoodInsight
        fields = [
            'id', 'property', 'insight_type', 'name', 'address',
            'distance_km', 'rating', 'lat', 'lng', 'notes',
            'added_by', 'added_by_name', 'created_at',
        ]
        read_only_fields = ['property', 'added_by', 'created_at']

    def get_added_by_name(self, obj):
        if not obj.added_by:
            return None
        u = obj.added_by
        full = f"{u.first_name} {u.last_name}".strip()
        return full or u.username
