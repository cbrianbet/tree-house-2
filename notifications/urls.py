from django.urls import path

from .views import notification_list, notification_mark_read, notification_read_all

urlpatterns = [
    path('', notification_list, name='notification-list'),
    path('read-all/', notification_read_all, name='notification-read-all'),
    path('<int:pk>/read/', notification_mark_read, name='notification-mark-read'),
]
