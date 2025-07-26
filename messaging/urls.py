from django.urls import path
from .views import RegisterView, ProfileView, MessageListCreateView, MessageWithUserView

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('me/', ProfileView.as_view()),
    path('messages/', MessageListCreateView.as_view(), name='message-list-create'),
    path('messages/<int:user_id>/', MessageWithUserView.as_view(), name='message-with-user'),
]
