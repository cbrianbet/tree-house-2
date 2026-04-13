from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('message', 'New Message'),
                    ('maintenance', 'Maintenance Update'),
                    ('payment', 'Payment'),
                    ('payment_reminder', 'Payment Due Reminder'),
                    ('lease', 'Lease'),
                    ('dispute', 'Dispute'),
                    ('application', 'Application'),
                    ('new_listing', 'New Listing Match'),
                    ('moving', 'Moving Booking'),
                    ('account', 'Account Update'),
                ],
            ),
        ),
    ]
