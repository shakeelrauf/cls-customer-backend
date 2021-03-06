# Generated by Django 3.0.10 on 2021-02-06 13:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('key_door_finder', '0005_keyrequest_keyrequestquantity'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='keyrequestquantity',
            name='image_1',
        ),
        migrations.RemoveField(
            model_name='keyrequestquantity',
            name='image_2',
        ),
        migrations.CreateModel(
            name='KeyRequestImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='key_request')),
                ('key_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='key_door_finder.KeyRequest')),
            ],
        ),
    ]
