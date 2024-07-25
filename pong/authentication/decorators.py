from django.http import JsonResponse
from django.core.cache import cache
from functools import wraps
from os import getenv
import jwt


JWT_SECRET = getenv("JWT_SECRET")


def token_required(func):
    @wraps(func)
    async def wrapper(self, request, *args, **kwargs):
        """
        access_token의 유효성을 검사하는 데코레이터
        :header Authorization: 헤더 jwt에 access_token을 담아서 보낸다
        """
        encoded_jwt = request.headers.get("Authorization")
        if not encoded_jwt:
            return JsonResponse({"error": "No jwt in request"}, status=401)
        if encoded_jwt.startswith("Bearer "):
            encoded_jwt = encoded_jwt[7:]

        try:
            decoded_jwt = jwt.decode(encoded_jwt, JWT_SECRET, algorithms=["HS256"])
        except:
            return JsonResponse({"error": "Decoding jwt failed"}, status=401)

        access_token = decoded_jwt.get("access_token")
        if not access_token:
            return JsonResponse({"error": "No access token provided"}, status=401)

        is_valid_token = await cache.aget(f'user_data_{access_token}')
        if not is_valid_token:
            return JsonResponse({"error": "Invalid token"}, status=401)

        return await func(self, request, access_token)
    return wrapper