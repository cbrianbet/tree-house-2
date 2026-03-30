from rest_framework import serializers

from .models import Conversation, ConversationParticipant, Message


class ConversationParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = ConversationParticipant
        fields = ['id', 'user_id', 'username', 'first_name', 'last_name', 'last_read_at', 'joined_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_name', 'body', 'created_at']
        read_only_fields = ['id', 'conversation', 'sender', 'created_at']

    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip() or obj.sender.username


class ConversationSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'property', 'subject', 'created_by', 'created_at', 'participants', 'unread_count', 'last_message']
        read_only_fields = ['id', 'created_by', 'created_at']

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request:
            return 0
        user = request.user
        try:
            participant = obj.participants.get(user=user)
        except ConversationParticipant.DoesNotExist:
            return 0
        last_read = participant.last_read_at
        if last_read is None:
            return obj.messages.count()
        return obj.messages.filter(created_at__gt=last_read).count()

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if last is None:
            return None
        return {
            'id': last.id,
            'body': last.body,
            'sender': last.sender.username,
            'created_at': last.created_at,
        }
