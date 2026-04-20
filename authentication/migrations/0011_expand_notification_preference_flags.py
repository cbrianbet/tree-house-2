from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0010_mark_admin_role_users_staff'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationpreference',
            name='invoice_issued',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreference',
            name='payment_receipt_sent',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreference',
            name='maintenance_bid_received',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreference',
            name='maintenance_job_completed',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreference',
            name='lease_document_uploaded',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreference',
            name='lease_document_signed',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreference',
            name='dispute_status_change',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreference',
            name='dispute_new_message',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreference',
            name='direct_message_received',
            field=models.BooleanField(default=True),
        ),
    ]
