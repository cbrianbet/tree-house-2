from django.urls import path
from . import views

urlpatterns = [
    path('companies/', views.company_list, name='moving-company-list'),
    path('companies/<int:pk>/', views.company_detail, name='moving-company-detail'),
    path('bookings/', views.booking_list, name='moving-booking-list'),
    path('bookings/<int:pk>/', views.booking_detail, name='moving-booking-detail'),
    path('companies/<int:company_pk>/reviews/', views.review_list, name='moving-review-list'),
    path('companies/<int:company_pk>/reviews/<int:review_pk>/', views.review_detail, name='moving-review-detail'),
]
