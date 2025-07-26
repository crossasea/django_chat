from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import os

class User(AbstractUser):
    # Custom fields can go here
    email = models.EmailField(unique=True)

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="sent_messages", on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="received_messages", on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    media = models.ForeignKey('MediaStore', null=True, blank=True, on_delete=models.SET_NULL)

    is_read = models.BooleanField(default=False)  # NEW FIELD

    class Meta:
        ordering = ['-timestamp']

class Group(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='groupchats')
    admins = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='admin_of_groups')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    def add_member(self, user):
        self.members.add(user)

    def remove_member(self, user):
        self.members.remove(user)
        self.admins.remove(user)  # Remove from admin if kicked

    def add_admin(self, user):
        if user in self.members.all():
            self.admins.add(user)

    def remove_admin(self, user):
        self.admins.remove(user)

class GroupMessage(models.Model):
    group = models.ForeignKey(Group, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


def user_media_path(instance, filename):
    return os.path.join("uploads", str(instance.uploaded_by.id), filename)

class MediaStore(models.Model):
    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("document", "Document"),
    ]

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to=user_media_path)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def filename(self):
        return os.path.basename(self.file.name)