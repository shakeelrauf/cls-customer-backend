# Generated by Django 3.0.10 on 2021-01-19 10:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer_dashboard', '0004_auto_20210119_1201'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraccess',
            name='audit',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='useraccess',
            name='service_request',
            field=models.BooleanField(default=True),
        ),
    ]
