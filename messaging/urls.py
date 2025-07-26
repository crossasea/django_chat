from django.urls import path
from .views import RegisterView, ProfileView, MessageListCreateView, MessageWithUserView, mark_as_read, create_group, MediaUploadView

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('me/', ProfileView.as_view()),
    path('messages/', MessageListCreateView.as_view(), name='message-list-create'),
    path('messages/<int:user_id>/', MessageWithUserView.as_view(), name='message-with-user'),
    path('messages/<int:message_id>/read/', mark_as_read, name='mark-as-read'),
    path('groups/create/', create_group, name='create-group'),
    path("media/upload/", MediaUploadView.as_view(), name="media-upload"),
]
