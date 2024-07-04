from django.http import JsonResponse
from django.core.cache import cache
from functools import wraps
from os import getenv
import jwt


def login_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        """
        access_token의 유효성을 검사하는 데코레이터
        :param request의 헤더에 JWT를 사용
        """
        encoded_jwt = request.headers.get('jwt')
        JWT_SECRET = getenv("JWT_SECRET")
        decoded_jwt = jwt.decode(encoded_jwt, JWT_SECRET, algorithms=["HS256"])
        access_token = decoded_jwt.get("access_token")
        if not access_token:
            return JsonResponse({'error': 'No access token provided'}, status=401)

        if access_token.startswith('Bearer '):
            access_token = access_token[7:]

        is_valid_token = cache.get(access_token)
        if not is_valid_token:
            return JsonResponse({'error': 'Expired token'}, status=401)

        return func(request, *args, **kwargs)
    return wrapper