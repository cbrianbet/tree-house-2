from django.urls import path

from .views import (
    conversation_list_create,
    conversation_detail,
    message_list_create,
    conversation_mark_read,
)

urlpatterns = [
    path('conversations/', conversation_list_create, name='conversation-list-create'),
    path('conversations/<int:pk>/', conversation_detail, name='conversation-detail'),
    path('conversations/<int:pk>/messages/', message_list_create, name='message-list-create'),
    path('conversations/<int:pk>/read/', conversation_mark_read, name='conversation-mark-read'),
]
