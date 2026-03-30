from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('authentication', '0007_add_notification_preferences'),
        ('property', '0006_add_tenant_application'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dispute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dispute_type', models.CharField(
                    choices=[
                        ('rent', 'Rent'),
                        ('maintenance', 'Maintenance'),
                        ('noise', 'Noise'),
                        ('lease_terms', 'Lease Terms'),
                        ('deposit', 'Deposit'),
                        ('other', 'Other'),
                    ],
                    max_length=20,
                )),
                ('status', models.CharField(
                    choices=[
                        ('open', 'Open'),
                        ('under_review', 'Under Review'),
                        ('resolved', 'Resolved'),
                        ('closed', 'Closed'),
                    ],
                    default='open',
                    max_length=20,
                )),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='disputes_created',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('property', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='disputes',
                    to='property.property',
                )),
                ('unit', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='disputes',
                    to='property.unit',
                )),
                ('resolved_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='disputes_resolved',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.CreateModel(
            name='DisputeMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('dispute', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messages',
                    to='disputes.dispute',
                )),
                ('sender', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='dispute_messages',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
