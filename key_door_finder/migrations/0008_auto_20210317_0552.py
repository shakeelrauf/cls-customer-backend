# Generated by Django 3.0.10 on 2021-03-17 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('key_door_finder', '0007_auto_20210206_1857'),
    ]

    operations = [
        migrations.AddField(
            model_name='hwpictures',
            name='door_in_img',
            field=models.ImageField(default='', upload_to='hw_pic'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='hwpictures',
            name='door_out_img',
            field=models.ImageField(default='', upload_to='hw_pic'),
            preserve_default=False,
        ),
    ]
