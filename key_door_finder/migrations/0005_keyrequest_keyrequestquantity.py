# Generated by Django 3.0.10 on 2021-02-05 11:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('key_door_finder', '0004_delete_keyrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='KeyRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company', models.CharField(max_length=255)),
                ('address', models.CharField(max_length=255)),
                ('phone', models.CharField(max_length=255)),
                ('email', models.CharField(max_length=255)),
                ('authorize_customer', models.CharField(max_length=255)),
                ('purchase_order', models.CharField(max_length=255)),
                ('delivery_method', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(default='pending', max_length=255)),
                ('pickup_by', models.CharField(blank=True, max_length=255, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='key_request', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='KeyRequestQuantity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('key_code', models.CharField(max_length=255)),
                ('brand', models.CharField(max_length=255)),
                ('image_1', models.ImageField(upload_to='key_request')),
                ('image_2', models.ImageField(upload_to='key_request')),
                ('key_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requests', to='key_door_finder.KeyRequest')),
            ],
        ),
    ]
