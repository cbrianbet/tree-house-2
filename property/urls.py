from django.urls import path
from . import views

urlpatterns = [
    path('properties/', views.property_list_create, name='property-list-create'),
    path('properties/<int:pk>/', views.property_detail, name='property-detail'),
    path('properties/<int:property_id>/units/', views.unit_list_create, name='unit-list-create'),
    path('units/<int:pk>/', views.unit_detail, name='unit-detail'),
    path('units/<int:unit_id>/images/', views.unit_image_list_create, name='unit-image-list-create'),
    path('units/<int:unit_id>/lease/', views.lease_list_create, name='lease-list-create'),
    path('units/public/', views.public_units, name='public-units'),
]