# Generated by Django 3.0.10 on 2021-01-20 08:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer_dashboard', '0005_auto_20210119_1546'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filenumber',
            name='file_number',
            field=models.CharField(max_length=255),
        ),
    ]
