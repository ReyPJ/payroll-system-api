# Generated by Django 5.1.5 on 2025-05-08 04:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employee', '0004_employee_unique_pin'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='qr_code',
            field=models.TextField(blank=True, null=True),
        ),
    ]
