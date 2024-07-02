from django.http import JsonResponse
from functools import wraps
import requests


def login_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        """
        access_token의 유효성을 검사하는 데코레이터
        :param request의 헤더에 'Authorization' name을 가진 value 사용
        """
        access_token = request.headers.get('Authorization')
        if not access_token:
            return JsonResponse({'error': 'No access token provided'}, status=401)

        if access_token.startswith('Bearer '):
            access_token = access_token[7:]

        is_valid_token = cache.get(access_token)
        if not is_valid_token:
            return JsonResponse({'error': 'Expired token'}, status=401)

        return func(request, *args, **kwargs)
    return wrapper