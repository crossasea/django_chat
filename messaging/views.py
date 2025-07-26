from rest_framework import generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Group, Message
from .serializers import RegisterSerializer, UserSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import MediaStoreSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

class ProfileView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


from rest_framework import generics, permissions
from .models import Message, User
from .serializers import MessageSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(recipient=user)

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

class MessageWithUserView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        other_user_id = self.kwargs['user_id']
        user = self.request.user
        try:
            other_user = User.objects.get(id=other_user_id)
        except User.DoesNotExist:
            raise NotFound("Recipient not found")

        return Message.objects.filter(
            sender__in=[user, other_user],
            recipient__in=[user, other_user]
        )
from rest_framework.decorators import api_view, permission_classes

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request, message_id):
    try:
        message = Message.objects.get(id=message_id, recipient=request.user)
    except Message.DoesNotExist:
        return Response({"detail": "Message not found."}, status=404)

    message.is_read = True
    message.save()

    return Response({"status": "marked as read"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_group(request):
    name = request.data.get('name')
    if not name:
        return Response({'error': 'Name is required'}, status=400)

    group = Group.objects.create(name=name, created_by=request.user)
    group.members.add(request.user)
    group.admins.add(request.user)
    return Response({'message': 'Group created', 'group_id': group.id})


class MediaUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MediaStoreSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(uploaded_by=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)