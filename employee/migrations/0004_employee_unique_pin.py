# Generated by Django 5.1.5 on 2025-05-06 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employee', '0003_employee_biweekly_hours_employee_night_shift_factor'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='unique_pin',
            field=models.CharField(blank=True, max_length=10, null=True, unique=True),
        ),
    ]
