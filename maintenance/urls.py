from django.urls import path
from . import views

urlpatterns = [
    path('requests/', views.request_list_create, name='maintenance-request-list'),
    path('requests/<int:pk>/', views.request_detail, name='maintenance-request-detail'),
    path('requests/<int:pk>/bids/', views.bid_list_create, name='maintenance-bid-list'),
    path('requests/<int:pk>/bids/<int:bid_id>/', views.bid_detail, name='maintenance-bid-detail'),
    path('requests/<int:pk>/timeline/', views.request_timeline, name='maintenance-request-timeline'),
    path('requests/<int:pk>/notes/', views.note_list_create, name='maintenance-note-list'),
    path('requests/<int:pk>/images/', views.image_list_create, name='maintenance-image-list'),
]
