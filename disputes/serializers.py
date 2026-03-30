from rest_framework import serializers

from .models import Dispute, DisputeMessage


class DisputeMessageSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = DisputeMessage
        fields = ['id', 'dispute', 'sender', 'sender_name', 'body', 'created_at']
        read_only_fields = ['id', 'dispute', 'sender', 'created_at']

    def get_sender_name(self, obj):
        name = f"{obj.sender.first_name} {obj.sender.last_name}".strip()
        return name if name else obj.sender.username


class DisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = [
            'id', 'created_by', 'property', 'unit', 'dispute_type', 'status',
            'title', 'description', 'resolved_by', 'resolved_at', 'created_at',
        ]
        read_only_fields = ['id', 'created_by', 'status', 'resolved_by', 'resolved_at', 'created_at']
