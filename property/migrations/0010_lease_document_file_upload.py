from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('property', '0009_tenant_invitation'),
    ]

    operations = [
        migrations.AddField(
            model_name='leasedocument',
            name='file',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='property.models.lease_document_upload_to',
            ),
        ),
        migrations.AlterField(
            model_name='leasedocument',
            name='file_url',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
