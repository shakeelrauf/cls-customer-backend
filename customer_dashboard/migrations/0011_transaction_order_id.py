# Generated by Django 3.0.10 on 2021-01-28 08:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer_dashboard', '0010_transaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='order_id',
            field=models.CharField(default=None, max_length=255),
            preserve_default=False,
        ),
    ]
