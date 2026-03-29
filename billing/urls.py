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
    # Charge types
    path('properties/<int:property_pk>/charge-types/', views.charge_type_list_create, name='charge-type-list'),
    path('properties/<int:property_pk>/charge-types/<int:pk>/', views.charge_type_detail, name='charge-type-detail'),
    # Additional income
    path('properties/<int:property_pk>/additional-income/', views.additional_income_list_create, name='additional-income-list'),
    path('properties/<int:property_pk>/additional-income/<int:pk>/', views.additional_income_detail, name='additional-income-detail'),
    # Expenses
    path('properties/<int:property_pk>/expenses/', views.expense_list_create, name='expense-list'),
    path('properties/<int:property_pk>/expenses/<int:pk>/', views.expense_detail, name='expense-detail'),
    # Financial report
    path('reports/<int:property_pk>/', views.financial_report, name='financial-report'),
]
