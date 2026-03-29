from django.urls import path
from . import views

urlpatterns = [
    path('config/<int:property_id>/', views.billing_config, name='billing-config'),
    path('invoices/', views.invoice_list, name='invoice-list'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice-detail'),
    path('invoices/<int:pk>/pay/', views.pay_invoice, name='invoice-pay'),
    path('invoices/<int:pk>/payments/', views.invoice_payments, name='invoice-payments'),
    path('receipts/', views.receipt_list, name='receipt-list'),
    path('receipts/<int:pk>/', views.receipt_detail, name='receipt-detail'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe-webhook'),
]
