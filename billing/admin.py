from django.contrib import admin

from .models import (
    AdditionalIncome,
    BillingConfig,
    ChargeType,
    Expense,
    Invoice,
    Payment,
    PropertyBillingNotificationSettings,
    Receipt,
    ReminderLog,
)

admin.site.register(BillingConfig)
admin.site.register(PropertyBillingNotificationSettings)
admin.site.register(Invoice)
admin.site.register(Payment)
admin.site.register(Receipt)
admin.site.register(ReminderLog)
admin.site.register(ChargeType)
admin.site.register(AdditionalIncome)
admin.site.register(Expense)
