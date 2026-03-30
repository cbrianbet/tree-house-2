from django.urls import path
from . import views

urlpatterns = [
    path('properties/<int:property_pk>/insights/', views.insight_list, name='neighborhood-insight-list'),
    path('properties/<int:property_pk>/insights/<int:insight_pk>/', views.insight_detail, name='neighborhood-insight-detail'),
]
