from django.urls import path

from . import views

urlpatterns = [
    path('', views.dispute_list_create, name='dispute-list-create'),
    path('<int:pk>/', views.dispute_detail, name='dispute-detail'),
    path('<int:pk>/messages/', views.dispute_message_list_create, name='dispute-message-list-create'),
]
