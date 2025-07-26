from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
import jwt

User = get_user_model()

@database_sync_to_async
def get_user(validated_token):
    try:
        user_id = validated_token.get("user_id")
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        try:
            headers = dict(scope["headers"])
            print("HEADERS:", headers)

            token = None
            auth_header = headers.get(b'authorization')
            if auth_header:
                try:
                    prefix, token_str = auth_header.decode().split()
                    if prefix.lower() == "bearer":
                        token = token_str
                except ValueError:
                    print("Malformed auth header")

            if not token:
                query_string = scope.get("query_string", b"").decode()
                query_params = parse_qs(query_string)
                token = query_params.get("token", [None])[0]

            if token:
                validated = UntypedToken(token)
                scope["user"] = await get_user(validated)
                print("Authenticated:", scope["user"])
            else:
                print("No token found")
                scope["user"] = AnonymousUser()

            return await super().__call__(scope, receive, send)
        except Exception as e:
            print("Middleware error:", e)
            raise e
