# Generated by Django 5.1.3 on 2024-11-29 22:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_user_fullname_user_photo_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chat',
            name='avatar_url',
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='photo_url',
            field=models.TextField(null=True),
        ),
    ]
