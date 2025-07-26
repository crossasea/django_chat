from rest_framework import serializers
from .models import User, MediaStore, Group, GroupMessage, Message

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    recipient_username = serializers.CharField(source="recipient.username", read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'recipient', 'sender_username', 'recipient_username', 'content', 'timestamp', 'is_read']
        read_only_fields = ['sender', 'timestamp', 'is_read']

class MediaStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaStore
        fields = ['id', 'file', 'media_type', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def validate_file(self, file):
        allowed_types = {
            "image": ["image/jpeg", "image/png"],
            "video": ["video/mp4", "video/quicktime"],
            "audio": ["audio/mpeg", "audio/wav"],
            "document": ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        }

        media_type = self.initial_data.get("media_type")
        if media_type not in allowed_types:
            raise serializers.ValidationError("Unsupported media type.")

        if file.content_type not in allowed_types[media_type]:
            raise serializers.ValidationError("File format not allowed for this media type.")

        return file