from django.urls import path
from . import views

urlpatterns = [
    # Admin
    path('admin/', views.admin_overview, name='dashboard-admin-overview'),
    path('admin/users/', views.admin_users, name='dashboard-admin-users'),
    path('admin/users/<int:pk>/', views.admin_user_detail, name='dashboard-admin-user-detail'),
    path('admin/moderation/reviews/', views.admin_moderation_reviews, name='dashboard-admin-reviews'),
    path('admin/moderation/reviews/<int:pk>/', views.admin_moderation_review_delete, name='dashboard-admin-review-delete'),

    # Role-specific dashboards
    path('tenant/', views.tenant_dashboard, name='dashboard-tenant'),
    path('artisan/', views.artisan_dashboard, name='dashboard-artisan'),
    path('agent/', views.agent_dashboard, name='dashboard-agent'),
    path('moving-company/', views.moving_company_dashboard, name='dashboard-moving-company'),
]
