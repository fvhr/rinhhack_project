from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    id = models.BigIntegerField(primary_key=True)
    photo_url = models.TextField(null=True)
    username = models.CharField(max_length=150, null=True)
    is_premium = models.BooleanField(default=False)

    USERNAME_FIELD = 'id'

    def __str__(self):
        return self.username


class Chat(models.Model):
    id = models.BigIntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)
    url = models.CharField(max_length=255, null=True)
    avatar_url = models.TextField(null=True)
    bot_is_admin = models.BooleanField(default=False)
    objects: models.Manager

    def __str__(self):
        return self.title


class UsersChats(models.Model):
    user = models.ForeignKey(User, models.CASCADE, 'chats')
    chat = models.ForeignKey(Chat, models.CASCADE, 'users')
    is_admin = models.BooleanField(default=False)
    objects: models.Manager
