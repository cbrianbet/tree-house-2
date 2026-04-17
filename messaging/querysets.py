"""
Optimized Conversation querysets for list/detail/create responses.

Migration notes (FE):
- Prefer participants[].user_id and last_message.sender (user pk) + sender_name.
- participants[].user mirrors user_id for legacy clients (previously inconsistent).
- last_message.sender is the sender's user id (aligned with GET .../messages/ rows).
- last_message.sender_username holds the old string that used to live under sender.
"""
from django.db.models import (
    CharField,
    Count,
    DateTimeField,
    F,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce, Concat, NullIf, Trim

from .models import Conversation, ConversationParticipant, Message


def conversations_queryset_for_user(user):
    """
    Single-query friendly Conversation queryset: unread_count and last_message
    fields are annotated; participants are prefetched with user + role.
    """
    user_last_read = Subquery(
        ConversationParticipant.objects.filter(
            conversation_id=OuterRef('pk'),
            user_id=user.pk,
        ).values('last_read_at')[:1]
    )

    latest_base = Message.objects.filter(conversation_id=OuterRef('pk')).order_by('-created_at')

    qs = (
        Conversation.objects.filter(participants__user=user)
        .select_related('created_by', 'created_by__role', 'property')
        .prefetch_related(
            Prefetch(
                'participants',
                queryset=ConversationParticipant.objects.select_related(
                    'user', 'user__role'
                ).order_by('id'),
            ),
        )
        .distinct()
        .annotate(_user_last_read=user_last_read)
        .annotate(
            _unread_count=Count(
                'messages',
                filter=Q(messages__created_at__gt=F('_user_last_read'))
                | Q(_user_last_read__isnull=True),
            )
        )
        .annotate(
            _lm_id=Subquery(latest_base.values('id')[:1]),
            _lm_body=Subquery(latest_base.values('body')[:1]),
            _lm_created_at=Subquery(latest_base.values('created_at')[:1]),
            _lm_sender_id=Subquery(latest_base.values('sender_id')[:1]),
            _lm_sender_username=Subquery(
                latest_base.values('sender__username')[:1], output_field=CharField()
            ),
            _lm_sender_name=Subquery(
                Message.objects.filter(conversation_id=OuterRef('pk'))
                .order_by('-created_at')
                .annotate(
                    _sn=Coalesce(
                        NullIf(
                            Trim(
                                Concat(
                                    F('sender__first_name'),
                                    Value(' '),
                                    F('sender__last_name'),
                                )
                            ),
                            Value(''),
                        ),
                        F('sender__username'),
                    )
                )
                .values('_sn')[:1],
                output_field=CharField(),
            ),
        )
    )
    qs = qs.annotate(
        _sort_ts=Coalesce(F('_lm_created_at'), F('created_at'), output_field=DateTimeField()),
    )
    return qs.order_by(F('_sort_ts').desc(nulls_last=True), '-id')


def get_conversation_for_user(*, user, pk):
    """Fetch one conversation with the same annotations/prefetch as list."""
    return conversations_queryset_for_user(user).get(pk=pk)
