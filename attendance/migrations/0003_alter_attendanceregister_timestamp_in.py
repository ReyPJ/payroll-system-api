# Generated by Django 5.1.5 on 2025-05-06 02:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0002_attendanceregister_paid_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendanceregister',
            name='timestamp_in',
            field=models.DateTimeField(),
        ),
    ]
