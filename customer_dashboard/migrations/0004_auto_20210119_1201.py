# Generated by Django 3.0.10 on 2021-01-19 06:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer_dashboard', '0003_auto_20201229_1701'),
    ]

    operations = [
        migrations.AddField(
            model_name='filenumber',
            name='location',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='filenumber',
            name='file_number',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
